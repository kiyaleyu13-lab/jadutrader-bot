import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from PIL import Image
import io

# Logging ማስተካከያ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

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
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # ፎቶውን በመጠን መቀነስ
        image = Image.open(io.BytesIO(photo_bytes))
        image.thumbnail((1024, 1024))

        analysis_prompt = """
        You are an expert Forex, Crypto, and Smart Money Concepts (SMC) Trader.
        Analyze the provided trading chart image in detail and provide the analysis in Amharic language using clear formatting:
        1. 📊 Trend & Market Structure (BOS, CHOCH)
        2. 🏦 SMC Elements (Order Blocks, FVG)
        3. 📉 Support & Resistance
        4. 🌍 Fundamental & Forex Factory News Context
        5. 🎯 Trade Setup (Bias, Entry, SL, TP)
        Keep it professional and entirely in Amharic.
        """

        response = ai_client.models.generate_content(
            model='gemini-3.8-flash',
            contents=[image, analysis_prompt]
        )

        if response and hasattr(response, 'text') and response.text:
            await status_msg.edit_text(response.text)
        else:
            await status_msg.edit_text("❌ ኤአይ ሞዴሉ ምላሽ አልሰጠም፣ እባክዎ እንደገና ይሞክሩ።")

    except Exception as e:
        logging.error(f"Error during analysis: {e}")
        await status_msg.edit_text(f"❌ ስህተት ተፈጥሯል: {str(e)}")

# Global Error Handler (ኤረር ሲኖር በሎግ እንዲመዘገብ)
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

# Main Function
def main():
    if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
        print("❌ እባክህ TELEGRAM_BOT_TOKEN እና GEMINI_API_KEY በ Environment Variables ውስጥ አስገባ!")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Error Handler ማስገባት
    app.add_error_handler(error_handler)

    print("🚀 ቦቱ መስራት ጀምሯል...")
    app.run_polling()

if __name__ == '__main__':
    main()
