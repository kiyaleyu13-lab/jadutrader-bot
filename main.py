import os
import logging
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
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

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ACTIVE_CHAT_IDS.add(chat_id)
    
    welcome_text = (
        "ሰላም! እኔ የ AI Forex & SMC Trading Analyst ቦት ነኝ። 🤖📊\n\n"
        "✅ አሁን ቦቱ እጅግ ፈጣን በሆነ መልኩ ይሰራል!\n"
        "የምንዛሬ ወይም የክሪፕቶ የChart ስክሪንሾት ላክልኝ፤ በሰከንዶች ውስጥ ትንተና እና ሴታፕ እልክልሃለሁ።"
    )
    await update.message.reply_text(welcome_text)

# አውቶማቲክ የዜና ማሳሰቢያ በጀርባ (Background Task) የሚሰራ
async def periodic_news_sender(application):
    await asyncio.sleep(10)
    while True:
        try:
            if ACTIVE_CHAT_IDS:
                news_prompt = """
                Provide a quick, high-impact daily Forex market and news briefing in Amharic. 
                Keep it concise and professional.
                """
                
                response = ai_client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=[news_prompt]
                )
                
                if response and hasattr(response, 'text') and response.text:
                    news_text = f"📰 **የገበያ እና ፋንዳሜታል ዜና ማሳሰቢያ**\n\n{response.text}"
                    
                    for chat_id in list(ACTIVE_CHAT_IDS):
                        try:
                            await application.bot.send_message(chat_id=chat_id, text=news_text)
                        except Exception as e:
                            logging.error(f"Failed to send news to {chat_id}: {e}")
            
            await asyncio.sleep(21600) 
        except Exception as e:
            logging.error(f"Error in periodic news sender: {e}")
            await asyncio.sleep(300)

# የChart ፎቶ ተቀብሎ በፍጥነት የመተንተን ተግባር
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ACTIVE_CHAT_IDS.add(chat_id)
    
    status_msg = await update.message.reply_text("⏳ ቻርቱን በፍጥነት እየተነተንኩ ነው...")

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # ፎቶውን መጠኑን መቀነስ (ለፈጣን AI ማቀናበሪያ)
        image = Image.open(io.BytesIO(photo_bytes))
        image.thumbnail((800, 800))

        # አጭር እና ፈጣን ፕረምፕ
        analysis_prompt = """
        Analyze this Forex/Crypto chart and provide in Amharic:
        1. 📊 Trend & SMC (BOS, CHOCH, Order Blocks)
        2. 📉 Key Support & Resistance
        3. 🎯 Trade Setup (Bias, Entry, SL, TP)
        4. 🛡️ Required Confirmation before entry
        Keep it concise, structured, and entirely in Amharic.
        """

        response = ai_client.models.generate_content(
            model='gemini-3.8-flash',
            contents=[image, analysis_prompt]
        )

        if response and hasattr(response, 'text') and response.text:
            analysis_text = response.text

            draw_image = image.copy()
            width, height = draw_image.size
            banner_height = 60
            new_image = Image.new("RGB", (width, height + banner_height), (20, 20, 20))
            new_image.paste(draw_image, (0, 0))
            
            draw_banner = ImageDraw.Draw(new_image)
            draw_banner.text((15, height + 20), "🤖 Jadu AI Forex & SMC Signal Bot", fill=(0, 255, 128))

            bio = io.BytesIO()
            bio.name = 'signal_chart.jpg'
            new_image.save(bio, 'JPEG')
            bio.seek(0)

            await status_msg.delete()
            await update.message.reply_photo(photo=bio, caption=analysis_text)
        else:
            await status_msg.edit_text("❌ ኤአይ ሞዴሉ ምላሽ አልሰጠም፣ እባክዎ እንደገና ይሞክሩ።")

    except Exception as e:
        logging.error(f"Error during analysis: {e}")
        await status_msg.edit_text(f"❌ ስህተት ተፈጥሯል: {str(e)}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

def main():
    if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
        print("❌ እባክህ TELEGRAM_BOT_TOKEN እና GEMINI_API_KEY በ Environment Variables ውስጥ አስገባ!")
        return

    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_error_handler(error_handler)

    async def post_init(application):
        asyncio.create_task(periodic_news_sender(application))

    app.post_init = post_init

    print("🚀 ቦቱ እጅግ ፈጣን በሆነ ሁነታ ስራ ጀምሯል...")
    app.run_polling()

if __name__ == '__main__':
    main()
