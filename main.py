import os
import logging
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from PIL import Image, ImageDraw
import io

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
news_task = None  # የታስኩን ሁኔታ ለመቆጣጠር

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
        "✅ እለታዊ Forex Factory ዜናዎች፣ SMC ትንተና፣ Entry፣ SL እና TP በዝርዝር ተዘጋጅተዋል!\n"
        "የቻርት ስክሪንሾት በመላክ ሙሉ ሴታፕ ማግኘት ይችላሉ፤ ወይም ከታች ያሉትን አዝራሮች ይጠቀሙ።"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

# አውቶማቲክ የዜና ማሳሰቢያ በጀርባ (Background Task) የሚሰራ (ለስላሳ ስረዛ ያለው)
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

# የጽሁፍ መልዕክቶችን እና አዝራሮችን አስተናጋጅ
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id
    ACTIVE_CHAT_IDS.add(chat_id)

    if text == "🚀 Start / ቦቱን አንቃ":
        await update.message.reply_text("🚀 ቦቱ ሙሉ በሙሉ ንቁ (Active) ነው! የሚፈልጉትን የቻርት ስክሪንሾት መላክ ይችላሉ።", reply_markup=get_main_keyboard())
    elif text == "📰 እለታዊ Forex Factory ዜና":
        await fetch_and_send_news(update, context)
    elif text == "ℹ️ መመሪያ እና እርዳታ":
        help_text = (
            "📌 **የቦቱ አጠቃቀም መመሪያ:**\n\n"
            "1. 📊 ማንኛውንም የ Forex ወይም Crypto ቻርት ስክሪንሾት በቀጥታ ይላኩ።\n"
            "2. ቦቱ የ **SMC ትንተና** (BOS, CHOCH, Order Blocks, FVG)፣ **Entry**፣ **SL** እና **TP** በዝርዝር ያዘጋጅልዎታል።\n"
            "3. **እለታዊ Forex Factory ዜናዎችን** ለማግኘት ከታች ያለውን አዝራር ይጠቀሙ።"
        )
        await update.message.reply_text(help_text, reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text("አማራጭ ይምረጡ ወይም ቻርት ስክሪንሾት ይላኩ።", reply_markup=get_main_keyboard())

# የChart ፎቶ ተቀብሎ ሙሉ SMC እና Trade Setup (Entry, SL, TP) የመተንተን ተግባር
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ACTIVE_CHAT_IDS.add(chat_id)
    
    status_msg = await update.message.reply_text("⏳ ቻርቱን በዝርዝር እየተነተንኩ፣ SMC ሴታፕ፣ Entry፣ SL እና TP እያዘጋጀሁ ነው...", reply_markup=get_main_keyboard())

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await asyncio.wait_for(photo_file.download_as_bytearray(), timeout=30.0)
        
        image = Image.open(io.BytesIO(photo_bytes))
        image.thumbnail((1024, 1024))

        analysis_prompt = """
        You are an expert Forex, Crypto, and Smart Money Concepts (SMC) Trader.
        Analyze the provided trading chart image in detail and provide a comprehensive analysis in Amharic language using clear formatting:
        
        1. 📊 Trend & Market Structure (BOS, CHOCH)
        2. 🏦 SMC Elements (Order Blocks, FVG, Liquidity Sweeps)
        3. 📉 Support & Resistance Levels
        4. 🌍 Fundamental & Forex Factory News Context
        5. 🎯 **Trade Setup**: 
           - Bias (BUY/SELL)
           - Entry Price (የመግቢያ ዋጋ)
           - Stop Loss - SL (ማቆሚያ ዋጋ)
           - Take Profit - TP (የትርፍ ኢላማዎች: TP 1 & TP 2)
           - Risk to Reward Ratio
        6. 🛡️ **Required Confirmations & Risk Management**: 
           - ገበያው ወደዚህ ሴታፕ ሲደርስ መግባት ከመወሰኑ በፊት ሊጠበቁ የሚገቡ የዋጋ ማረጋገጫዎች እና የገንዘብ አያያዝ (Risk Management) ማሳሰቢያ።

        Keep it professional, structured, and entirely in Amharic.
        """

        loop = asyncio.get_running_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None, 
                lambda: ai_client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=[image, analysis_prompt]
                )
            ),
            timeout=50.0
        )

        if response and hasattr(response, 'text') and response.text:
            analysis_text = response.text

            draw_image = image.copy()
            width, height = draw_image.size
            banner_height = 80
            new_image = Image.new("RGB", (width, height + banner_height), (20, 20, 20))
            new_image.paste(draw_image, (0, 0))
            
            draw_banner = ImageDraw.Draw(new_image)
            draw_banner.text((20, height + 25), "🤖 Jadu AI Forex & SMC Signal Bot", fill=(0, 255, 128))

            bio = io.BytesIO()
            bio.name = 'signal_chart.jpg'
            new_image.save(bio, 'JPEG')
            bio.seek(0)

            await status_msg.delete()
            await update.message.reply_photo(photo=bio, caption=analysis_text, reply_markup=get_main_keyboard())
        else:
            await status_msg.edit_text("❌ ኤአይ ሞዴሉ ምላሽ አልሰጠም፣ እባክዎ እንደገና ይሞክሩ።", reply_markup=get_main_keyboard())

    except asyncio.TimeoutError:
        logging.error("Analysis operation timed out.")
        await status_msg.edit_text("⏱️ ትንተናው ትንሽ ጊዜ ወስዷል። እባክዎ ቻርቱን እንደገና ይላኩ።", reply_markup=get_main_keyboard())
    except Exception as e:
        logging.error(f"Error during analysis: {e}")
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
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
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

    print("🚀 ቦቱ ሙሉ ትንተና እና ዜና ማሳሰቢያ ሁነታ ስራ ጀምሯል...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
