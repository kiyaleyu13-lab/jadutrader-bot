import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types
from PIL import Image
import io

# Logging ማስተካከያ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Render Port Timeout ለመከላከል የሚረዳ ትንሽ ዌብ ሰርቨር
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Jadutrader_bot is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logging.info(f"🌐 ዌብ ሰርቨር በፖርት {port} ላይ ተጀምሯል...")
    server.serve_forever()

# API Keys
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini Client ማዘጋጀት
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "ሰላም! እኔ የ AI Forex & SMC Trading Analyst ቦት ነኝ። 🤖📊\n\n"
        "የምንዛሬ ወይም የክሪፕቶ የChart ስክሪንሾት ላክልኝ፤ "
        "እኔ ደግሞ Technical Analysis፣ SMC Analysis እና Trade Setup አዘጋጅቼ እልክልሃለሁ!"
    )
    await update.message.reply_text(welcome_text)

# የChart ፎቶ ተቀብሎ የመተንተን ተግባር
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⏳ የChart ፎቶህን እየተነተንኩ ነው... እባክህ ትንሽ ጠብቀኝ...")

    try:
        # ፎቶውን ከቴሌግራም ማውረድ
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # ፎቶውን ወደ PIL Image መቀየር
        image = Image.open(io.BytesIO(photo_bytes))

        analysis_prompt = """
        You are an expert Forex, Crypto, and Smart Money Concepts (SMC) Trader, as well as a Macroeconomic Analyst.
        Analyze the provided trading chart image in detail and provide a comprehensive analysis in Amharic language using clear formatting:

        1. 📊 **Trend & Market Structure**: Overall trend, BOS, and CHOCH.
        2. 🏦 **SMC Elements**: Order Blocks (OB), FVG, and Liquidity Sweeps.
        3. 📉 **Technical Levels**: Major Support and Resistance.
        4. 🌍 **Fundamental & News Context**: ወቅታዊ ከዚህ ንብረት (Asset - ለምሳሌ ወርቅ/Gold ወይም ዩኤስዲ) ጋር ተያዥነት ያላቸው ማክሮ ኢኮኖሚ ዜናዎች፣ የወለድ መጠን፣ የዋጋ ንረት (Inflation) ወይም ጂኦፖለቲካዊ ሁኔታዎች አጠቃላይ ተፅዕኖ።
        5. 🎯 **Trade Setup**: Bias (BUY/SELL), Entry, SL, TP, RR.
        6. ⚠️ **Risk Warning**.

        Keep the explanation professional, insightful, and completely in Amharic.
        """   
# በ Gemini AI ፎቶውን መተንተን
        response = ai_client.models.generate_content(
            model='gemini-3.8-flash',  # እዚህ ጋር gemini-3.8-flash ብለህ አስገባ
            contents=[image, analysis_prompt]
        )


        # ውጤቱን ለተጠቃሚው መላክ
        await status_msg.edit_text(response.text)

    except Exception as e:
        logging.error(f"Error during analysis: {e}")
        # ትክክለኛው ኤረር ምን እንደሆነ በቴሌግራም እንዲነግረን እናደርጋለን
        await status_msg.edit_text(f"❌ ኤረር አጋጥሟል: {str(e)}")

# Main Function
def main():
    if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
        print("❌ እባክህ TELEGRAM_BOT_TOKEN እና GEMINI_API_KEY በ Environment Variables ውስጥ አስገባ!")
        return

    # ዌብ ሰርቨርን በ Background Thread ማስጀመር
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🚀 ቦቱ መስራት ጀምሯል...")
    app.run_polling()

if __name__ == '__main__':
    main()
