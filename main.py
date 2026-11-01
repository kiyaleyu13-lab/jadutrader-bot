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
        "ሰላም! እኔ የ AI Forex & SMC Trading Analyst ቦት ነኝ። 🤖⚡\n\n"
        "🚀 አሁን ፍጥነቱ ተስተካክሏል! የሳንቲሙን ስም ብቻ (ለምሳሌ: `XAUUSD` ወይም `EURUSD`) ይጻፉ።\n"
        "ቦቱ ዋና ዋና ነጥቦቹን ብቻ (Bias, Entry, SL, TP) በአጭር ጊዜ ውስጥ ይሰጥዎታል።"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

# አውቶማቲክ የዜና ማሳሰቢያ በጀርባ (Background Task)
async def periodic_news_sender(application):
    await asyncio.sleep(15)
    try:
        while True:
            if ACTIVE_CHAT_IDS:
                news_prompt = """
                Provide a short and concise high-impact daily Forex Factory news summary in Amharic (only key bullet points).
                """
                
                response = ai_client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=[news_prompt]
                )
                
                if response and hasattr(response, 'text') and response.text:
                    news_text = f"📰 **አጭር የ Forex Factory ዜና ማጠቃለያ**\n\n{response.text}"
                    
                    for chat_id in list(ACTIVE_CHAT_IDS):
                        try:
                            await application.bot.send_message(chat_id=chat_id, text=news_text)
                        except Exception as e:
                            logging.error(f"Failed to send news to {chat_id}: {e}")
            
            await asyncio.sleep(21600) 
    except asyncio.CancelledError:
        logging.info("Periodic news task successfully cancelled.")

# ዜና ማምጫ ፌንክሽን (በዋና ዋና ነጥብ ብቻ)
async def fetch_and_send_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ACTIVE_CHAT_IDS.add(chat_id)
    
    status_msg = await update.message.reply_text("⏳ ዜናውን በአጭሩ እያዘጋጀሁ ነው...", reply_markup=get_main_keyboard())

    try:
        news_prompt = """
        Provide a concise daily Forex Factory macroeconomic news summary in Amharic, highlighting only high-impact events and market bias in brief bullet points.
        """
        
        response = ai_client.models.generate_content(
            model='gemini-3.8-flash',
            contents=[news_prompt]
        )

        if response and hasattr(response, 'text') and response.text:
            await status_msg.edit_text(f"📰 **የ Forex Factory ዜና ማጠቃለያ**\n\n{response.text}", reply_markup=get_main_keyboard())
        else:
            await status_msg.edit_text("❌ ዜናውን ማግኘት አልተቻለም።", reply_markup=get_main_keyboard())

    except Exception as e:
        logging.error(f"Error getting news: {e}")
        await status_msg.edit_text(f"❌ ስህተት ተፈጥሯል: {str(e)}", reply_markup=get_main_keyboard())

# የጽሁፍ መልዕክቶችን እና የሳንቲም ስሞችን አስተናጋጅ (ለፍጥነት ሲባል አጭር መልእክት ብቻ የሚሰጥ)
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id
    ACTIVE_CHAT_IDS.add(chat_id)

    if text == "🚀 Start / ቦቱን አንቃ":
        await update.message.reply_text("🚀 ቦቱ ዝግጁ ነው! የሚፈልጉትን የሳንቲም ስም (ለምሳሌ XAUUSD) ይጻፉ።", reply_markup=get_main_keyboard())
    elif text == "📰 እለታዊ Forex Factory ዜና":
        await fetch_and_send_news(update, context)
    elif text == "ℹ️ መመሪያ እና እርዳታ":
        help_text = (
            "📌 **አጭር መመሪያ:**\n\n"
            "የገበያ ጥንድ ስም ብቻ ይጻፉ (ለምሳሌ: **XAUUSD**, **EURUSD**)\n"
            "ቦቱ ዋና ዋና ነጥቦቹን ብቻ (Bias, Entry, SL, TP) በሰከንዶች ውስጥ በግልጽ ያሳዩዎታል።"
        )
        await update.message.reply_text(help_text, reply_markup=get_main_keyboard())
    else:
        # ፈጣን እና አጭር ትንተና (ዋና ዋና ነጥብ ብቻ)
        status_msg = await update.message.reply_text(f"⚡ የ **{text}** ዋና ዋና ሴታፖችን እያዘጋጀሁ ነው...", reply_markup=get_main_keyboard())
        
        try:
            analysis_prompt = f"""
            Analyze asset: {text} using SMC and provide ONLY a very short, concise trading signal in Amharic with bullet points:
            - 📊 Bias (BUY / SELL)
            - 🎯 Entry Price
            - 🛑 Stop Loss (SL)
            - 🎯 Take Profit (TP)
            - 🏦 Short SMC Reason (Order Block/FVG in 1 sentence)
            Keep it extremely brief and fast.
            """

            response = ai_client.models.generate_content(
                model='gemini-3.8-flash',
                contents=[analysis_prompt]
            )

            if response and hasattr(response, 'text') and response.text:
                await status_msg.edit_text(f"📊 **{text} - ፈጣን ሴታፕ**\n\n{response.text}", reply_markup=get_main_keyboard())
            else:
                await status_msg.edit_text("❌ መረጃውን ማግኘት አልተቻለም።", reply_markup=get_main_keyboard())

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

    print("🚀 ቦቱ በፈጣን (Short Summary) ሁነታ ስራ ጀምሯል...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
