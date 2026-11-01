import os
import logging
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# Logging ማስተካከያ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Render Port Timeout ለመከላከል የሚረዳ ዌብ ሰርቨር
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Jadutrader_bot is running successfully!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# API Keys
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini Client ማዘጋጀት
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# ተጠቃሚዎችን ለመያዝ የሚረዳ ዝርዝር
ACTIVE_CHAT_IDS = set()
news_task = None

# ቋሚ አዝራሮች
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🚀 Start / ቦቱን አንቃ"), KeyboardButton("📰 እለታዊ Forex Factory ዜና")],
        [KeyboardButton("ℹ️ መመሪያ እና እርዳታ")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ACTIVE_CHAT_IDS.add(chat_id)
    
    welcome_text = (
        "ሰላም! እኔ የ AI Forex & SMC Trading Analyst ቦት ነኝ። 🤖📊\n\n"
        "⚡ ፎቶ መላክ ሳይጠበቅብዎት የሳንቲሙን ስም (ለምሳሌ: `XAUUSD` ወይም `EURUSD`) በመጻፍ ብቻ ፈጣን የ SMC ትንተና፣ Entry፣ SL እና TP ማግኘት ይችላሉ!\n\n"
        "እለታዊ ዜናዎችን ለማግኘት ከታች ያሉትን አዝራሮች ይጠቀሙ።"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

# አውቶማቲክ የዜና ማሳሰቢያ በጀርባ (Background Task)
async def periodic_news_sender(application):
    await asyncio.sleep(15)
    try:
        while True:
            if ACTIVE_CHAT_IDS:
                news_prompt = """
                You are an expert Forex Fundamental Analyst and Forex Factory news strategist.
                Provide a detailed, professional daily market and Forex Factory news briefing in Amharic focusing on:
                1. 🌍 High-Impact Forex Factory News (CPI, NFP, Interest Rate decisions, GDP).
                2. 🪙 Market Sentiment on major pairs and Gold (XAUUSD).
                3. 💡 Professional advice on how traders should manage risk during these news events.
                Keep it highly structured, professional, and entirely in Amharic.
                """
                
                response = ai_client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=[news_prompt]
                )
                
                if response and hasattr(response, 'text') and response.text:
                    news_text = f"📰 **እለታዊ የ Forex Factory እና ማክሮ ኢኮኖሚ ዜና**\n\n{response.text}"
                    
                    for chat_id in list(ACTIVE_CHAT_IDS):
                        try:
                            await application.bot.send_message(chat_id=chat_id, text=news_text)
                        except Exception as e:
                            logging.error(f"Failed to send news to {chat_id}: {e}")
            
            await asyncio.sleep(21600) 
    except asyncio.CancelledError:
        logging.info("Periodic news task successfully cancelled.")

# ዜና ማምጫ ፌንክሽን
async def fetch_and_send_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ACTIVE_CHAT_IDS.add(chat_id)
    
    status_msg = await update.message.reply_text("⏳ እለታዊ የ Forex Factory ዜናዎችን እና የገበያ ትንተና እያዘጋጀሁ ነው...", reply_markup=get_main_keyboard())

    try:
        news_prompt = """
        Provide a current Forex Factory and macroeconomic daily news analysis in Amharic, highlighting key upcoming events, high-impact news, and market bias.
        Keep it professional and entirely in Amharic.
        """
        
        response = ai_client.models.generate_content(
            model='gemini-3.8-flash',
            contents=[news_prompt]
        )

        if response and hasattr(response, 'text') and response.text:
            await status_msg.edit_text(f"📰 **እለታዊ የ Forex Factory ዜና ትንተና**\n\n{response.text}", reply_markup=get_main_keyboard())
        else:
            await status_msg.edit_text("❌ ዜናውን ማግኘት አልተቻለም።", reply_markup=get_main_keyboard())

    except Exception as e:
        logging.error(f"Error getting news: {e}")
        await status_msg.edit_text(f"❌ ስህተት ተፈጥሯል: {str(e)}", reply_markup=get_main_keyboard())

# የጽሁፍ መልዕክቶችን እና የሳንቲም ስሞችን አስተናጋጅ (ፈጣን የጽሁፍ SMC ትንተና የሚሰጥበት)
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id
    ACTIVE_CHAT_IDS.add(chat_id)

    if text == "🚀 Start / ቦቱን አንቃ":
        await update.message.reply_text("🚀 ቦቱ ሙሉ በሙሉ ንቁ (Active) ነው! የሚፈልጉትን የሳንቲም ስም (ለምሳሌ XAUUSD) ይጻፉ።", reply_markup=get_main_keyboard())
    elif text == "📰 እለታዊ Forex Factory ዜና":
        await fetch_and_send_news(update, context)
    elif text == "ℹ️ መመሪያ እና እርዳታ":
        help_text = (
            "📌 **የቦቱ አጠቃቀም መመሪያ:**\n\n"
            "1. ⚡ ማንኛውንም የገበያ ጥንድ ስም (ለምሳሌ **XAUUSD**, **EURUSD**, **BTCUSD**) በቀጥታ ይጻፉ።\n"
            "2. ቦቱ ወዲያውኑ የ **SMC ትንተና**፣ **Entry**፣ **SL** እና **TP** በሰከንዶች ውስጥ በጽሁፍ ያዘጋጅልዎታል።\n"
            "3. **እለታዊ Forex Factory ዜናዎችን** ለማግኘት ከታች ያለውን አዝራር ይጠቀሙ።"
        )
        await update.message.reply_text(help_text, reply_markup=get_main_keyboard())
    else:
        # ተጠቃሚው የሳንቲም ስም ሲጽፍ (ለምሳሌ XAUUSD) በሰከንዶች ውስጥ የሚሰጥ ፈጣን ትንተና
        status_msg = await update.message.reply_text(f"⏳ ለ **{text}** የሚሆን የ SMC ትንተና እና ሴታፕ እያዘጋጀሁ ነው...", reply_markup=get_main_keyboard())
        
        try:
            analysis_prompt = f"""
            You are an expert Forex, Crypto, and Smart Money Concepts (SMC) Trader.
            Provide a professional and detailed trading analysis and signal setup in Amharic for the asset/symbol: {text}.
            
            Include the following sections clearly:
            1. 📊 Market Bias / Trend (BUY / SELL)
            2. 🏦 SMC Key Levels (Order Blocks, FVG)
            3. 🎯 **Trade Setup**:
               - Entry Price (የመግቢያ ዋጋ)
               - Stop Loss - SL (ማቆሚያ ዋጋ)
               - Take Profit - TP (የትርፍ ኢላማዎች: TP 1 & TP 2)
               - Risk to Reward Ratio
            4. 🛡️ Risk Management & Confirmations
            
            Keep it professional, structured, and entirely in Amharic.
            """

            response = ai_client.models.generate_content(
                model='gemini-3.8-flash',
                contents=[analysis_prompt]
            )

            if response and hasattr(response, 'text') and response.text:
                await status_msg.edit_text(f"📊 **የ {text} የ SMC ትንተና እና ሴታፕ**\n\n{response.text}", reply_markup=get_main_keyboard())
            else:
                await status_msg.edit_text("❌ ትንተናውን ማግኘት አልተቻለም። እባክዎ እንደገና ይሞክሩ።", reply_markup=get_main_keyboard())

        except Exception as e:
            logging.error(f"Error during text analysis: {e}")
            await status_msg.edit_text(f"❌ ስህተት ተፈጥሯል: {str(e)}", reply_markup=get_main_keyboard())

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

def main():
    global news_task
    if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
        print("❌ እባክህ API Keys አስገባ!")
        return

    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("news", fetch_and_send_news))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    app.add_error_handler(error_handler)

    async def post_init(application):
        global news_task
        news_task = asyncio.create_task(periodic_news_sender(application))

    async def shutdown(application):
        global news_task
        if news_task:
            news_task.cancel()
            try:
                await news_task
            except asyncio.CancelledError:
                pass

    app.post_init = post_init
    app.post_shutdown = shutdown

    print("🚀 ቦቱ በጽሁፍ ፈጣን ትንተና ሁነታ ስራ ጀምሯል...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
