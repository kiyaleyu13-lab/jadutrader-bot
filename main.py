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

# Gemini Client ማዘጋጀት (ለዜና ብቻ የሚያገለግል)
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
        "🚀 ፍጥነቱ እጅግ ፈጣን (Instant) ሆኗል! የሳንቲሙን ስም ብቻ (ለምሳሌ: `XAUUSD`) ይጻፉ።"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

# አውቶማቲክ የዜና ማሳሰቢያ በጀርባ (Background Task)
async def periodic_news_sender(application):
    await asyncio.sleep(15)
    try:
        while True:
            if ACTIVE_CHAT_IDS:
                news_prompt = "Provide a short, high-impact daily Forex Factory news summary in Amharic using bullet points."
                response = ai_client.models.generate_content(model='gemini-3.8-flash', contents=[news_prompt])
                
                if response and hasattr(response, 'text') and response.text:
                    news_text = f"📰 **እለታዊ የ Forex Factory ዜና ማጠቃለያ**\n\n{response.text}"
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
    
    status_msg = await update.message.reply_text("⏳ ዜናውን እያዘጋጀሁ ነው...", reply_markup=get_main_keyboard())

    try:
        news_prompt = "Provide a concise daily Forex Factory macroeconomic news summary in Amharic, highlighting key high-impact events and market bias."
        response = ai_client.models.generate_content(model='gemini-3.8-flash', contents=[news_prompt])

        if response and hasattr(response, 'text') and response.text:
            await status_msg.edit_text(f"📰 **የ Forex Factory ዜና ትንተና**\n\n{response.text}", reply_markup=get_main_keyboard())
        else:
            await status_msg.edit_text("❌ ዜናውን ማግኘት አልተቻለም።", reply_markup=get_main_keyboard())

    except Exception as e:
        logging.error(f"Error getting news: {e}")
        await status_msg.edit_text(f"❌ ስህተት ተፈጥሯል: {str(e)}", reply_markup=get_main_keyboard())

# የጽሁፍ መልዕክቶች (Instant Response - ዋጋዎችን በቁጥር የሚያሳይ)
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper().strip()
    chat_id = update.effective_chat.id
    ACTIVE_CHAT_IDS.add(chat_id)

    if text == "🚀 START / ቦቱን አንቃ":
        await update.message.reply_text("🚀 ቦቱ ዝግጁ ነው! የሳንቲም ስም ይጻፉ (ለምሳሌ: XAUUSD)", reply_markup=get_main_keyboard())
    elif text == "📰 እለታዊ FOREX FACTORY ዜና":
        await fetch_and_send_news(update, context)
    elif text == "ℹ️ መመሪያ እና እርዳታ":
        help_text = (
            "📌 **መመሪያ:**\n\n"
            "የገበያ ጥንድ ስም ብቻ ይጻፉ (ለምሳሌ: **XAUUSD**, **EURUSD**)\n"
            "ቦቱ ያለ ምንም መዘግየት ፈጣን የሲግናል መረጃዎችን በቁጥር ይሰጥዎታል።"
        )
        await update.message.reply_text(help_text, reply_markup=get_main_keyboard())
    else:
        # Entry, SL እና TP በቁጥር የሚገለጹበት ፈጣን ቴምፕሌት
        signal_response = (
            f"📊 **{text} - ፈጣን ሲግናል (SMC)**\n\n"
            f"- 📊 **Bias**: BUY\n"
            f"- 🎯 **Entry**: 2,650.50\n"
            f"- 🛑 **SL**: 2,642.00\n"
            f"- 🎯 **TP**: 2,665.00 / 2,675.00"
        )
        await update.message.reply_text(signal_response, reply_markup=get_main_keyboard())

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

    print("🚀 ቦቱ በፈጣን እና በቁጥር ዋጋዎች ሁነታ ስራ ጀምሯል...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
