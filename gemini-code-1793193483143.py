import os
import logging
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

# 1. API Keys (ከ Environment Variables ይወሰዳሉ)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini Client ማዘጋጀት
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# 2. Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "ሰላም! እኔ የ AI Forex & SMC Trading Analyst ቦት ነኝ። 🤖📊\n\n"
        "የምንዛሬ ወይም የክሪፕቶ የChart ስክሪንሾት (M5, M15, M30, H1, H4) ላክልኝ፤ "
        "እኔ ደግሞ Technical Analysis፣ SMC Analysis፣ Liquidity Sweep እና ሊታሰቡ የሚችሉ "
        "Entry, Stop Loss (SL), Take Profit (TP) ደረጃዎችን አዘጋጅቼ እልክልሃለሁ!"
    )
    await update.message.reply_text(welcome_text)

# 3. የChart ፎቶ ተቀብሎ የመተንተን ተግባር
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⏳ የChart ፎቶህን እየተነተንኩ ነው... እባክህ ትንሽ ጠብቀኝ...")

    try:
        # ፎቶውን ከቴሌግራም ማውረድ
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # ፎቶውን ወደ PIL Image መቀየር
        image = Image.open(io.BytesIO(photo_bytes))

        # ለ AI የሚሰጥ ዝርዝር Prompt (System Prompt)
        analysis_prompt = """
        You are an expert Forex, Crypto, and Smart Money Concepts (SMC) Trader.
        Analyze the provided trading chart image in detail and provide the analysis in Amharic language using clear formatting:

        1. 📊 **Trend & Market Structure**: Overall trend (Bullish/Bearish/Ranging), Break of Structure (BOS), and Change of Character (CHOCH).
        2. 🏦 **SMC Elements**: Identify key Order Blocks (OB), Fair Value Gaps (FVG), and Liquidity Sweeps if present.
        3. 📉 **Technical Levels**: Major Support and Resistance zones.
        4. 🎯 **Trade Setup Proposal (Educational only)**:
           - Potential Bias: (BUY / SELL)
           - Suggested Entry Zone
           - Stop Loss (SL)
           - Take Profit (TP1, TP2)
           - Risk to Reward Ratio
        5. ⚠️ **Risk Warning**: Remind the user to manage risk carefully.

        Keep the explanation professional, direct, structured, and completely in Amharic.
        """

        # በ Gemini AI ፎቶውን መተንተን
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[image, analysis_prompt]
        )

        # ውጤቱን ለተጠቃሚው መላክ
        await status_msg.edit_text(response.text)

    except Exception as e:
        logging.error(f"Error during analysis: {e}")
        await status_msg.edit_text("❌ አፎይ! ፎቶውን መተንተን አልተቻለም። እባክህ የፎቶውን ጥራት አረጋግጠህ እንደገና ሞክር።")

# Main Function
def main():
    if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
        print("❌ እባክህ TELEGRAM_BOT_TOKEN እና GEMINI_API_KEY በ Environment Variables ውስጥ አስገባ!")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🚀 ቦቱ መስራት ጀምሯል...")
    app.run_polling()

if __name__ == '__main__':
    main()