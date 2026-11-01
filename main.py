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
        "✅ ሙሉ ትንተና፣ SMC ሴታፕ፣ ማረጋገጫዎች (Confirmations) እና የ Forex Factory ዜናዎች ዝግጁ ናቸው!\n"
        "የምንዛሬ ወይም የክሪፕቶ የChart ስክሪንሾት ላክልኝ፤ ወይም /news በመጻፍ የዜና ትንተና ማግኘት ትችላለህ።"
    )
    await update.message.reply_text(welcome_text)

# አውቶማቲክ የዜና ማሳሰቢያ በጀርባ (Background Task) የሚሰራ
async def periodic_news_sender(application):
    await asyncio.sleep(15)
    while True:
        try:
            if ACTIVE_CHAT_IDS:
                news_prompt = """
                You are an expert Forex Fundamental Analyst and Forex Factory news strategist.
                Provide a detailed, professional daily and weekly market news briefing in Amharic focusing on:
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
                    news_text = f"📰 **የ Forex Factory እና ማክሮ ኢኮኖሚ የዜና ትንተና**\n\n{response.text}"
                    
                    for chat_id in list(ACTIVE_CHAT_IDS):
                        try:
                            await application.bot.send_message(chat_id=chat_id, text=news_text)
                        except Exception as e:
                            logging.error(f"Failed to send news to {chat_id}: {e}")
            
            # በየ 6 ሰዓቱ በራሱ ሰዓት ይልካል
            await asyncio.sleep(21600) 
        except Exception as e:
            logging.error(f"Error in periodic news sender: {e}")
            await asyncio.sleep(300)

# ተጠቃሚው በ ትዕዛዝ (/news) የገበያ እና የፋብሪካ ዜናዎችን ማግኘት ሲፈልግ
async def get_news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ACTIVE_CHAT_IDS.add(chat_id)
    
    status_msg = await update.message.reply_text("⏳ የ Forex Factory እና የገበያ ዜናዎችን እያዘጋጀሁ ነው...")

    try:
        news_prompt = """
        Provide a current Forex Factory and macroeconomic news analysis in Amharic, highlighting key upcoming events, high-impact news, and market bias.
        Keep it professional and entirely in Amharic.
        """
        
        response = ai_client.models.generate_content(
            model='gemini-3.8-flash',
            contents=[news_prompt]
        )

        if response and hasattr(response, 'text') and response.text:
            await status_msg.edit_text(f"📰 **የ Forex Factory ዜና ትንተና**\n\n{response.text}")
        else:
            await status_msg.edit_text("❌ ዜናውን ማግኘት አልተቻለም።")

    except Exception as e:
        logging.error(f"Error getting news: {e}")
        await status_msg.edit_text(f"❌ ስህተት ተፈጥሯል: {str(e)}")

# የChart ፎቶ ተቀብሎ በጥልቀት የመተንተን ተግባር (በ Timeout ጥበቃ)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ACTIVE_CHAT_IDS.add(chat_id)
    
    status_msg = await update.message.reply_text("⏳ ቻርቱን በዝርዝር እየተነተንኩ እና SMC ሴታፑን እያዘጋጀሁ ነው...")

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await asyncio.wait_for(photo_file.download_as_bytearray(), timeout=30.0)
        
        image = Image.open(io.BytesIO(photo_bytes))
        image.thumbnail((1024, 1024))

        # የጠለቀው እና የተሟላው ትንተና ፕረምፕ
        analysis_prompt = """
        You are an expert Forex, Crypto, and Smart Money Concepts (SMC) Trader.
        Analyze the provided trading chart image in detail and provide a comprehensive analysis in Amharic language using clear formatting:
        
        1. 📊 Trend & Market Structure (BOS, CHOCH)
        2. 🏦 SMC Elements (Order Blocks, FVG, Liquidity Sweeps)
        3. 📉 Support & Resistance Levels
        4. 🌍 Fundamental & Forex Factory News Context
        5. 🎯 Trade Setup (Bias: BUY/SELL, Entry Price, Stop Loss, Take Profit)
        6. 🛡️ **Required Confirmations (ማረጋገጫዎች)**: 
           - ገበያው ወደዚህ ሴታፕ ሲደርስ መግባት ከመወሰኑ በፊት ሊጠበቁ የሚገቡ የዋጋ ማረጋገጫዎች (ለምሳሌ: Rejection Candle, Lower Timeframe CHOCH)።
           - Risk Management ማሳሰቢያ።

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
            await update.message.reply_photo(photo=bio, caption=analysis_text)
        else:
            await status_msg.edit_text("❌ ኤአይ ሞዴሉ ምላሽ አልሰጠም፣ እባክዎ እንደገና ይሞክሩ።")

    except asyncio.TimeoutError:
        logging.error("Analysis operation timed out.")
        await status_msg.edit_text("⏱️ ትንተናው ትንሽ ጊዜ ወስዷል። እባክዎ ቻርቱን እንደገና ይላኩ።")
    except Exception as e:
        logging.error(f"Error during analysis: {e}")
        await status_msg.edit_text(f"❌ ስህተት ተፈጥሯል: {str(e)}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

def main():
    if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
        print("❌ እባክህ API Keys አስገባ!")
        return

    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("news", get_news_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_error_handler(error_handler)

    async def post_init(application):
        asyncio.create_task(periodic_news_sender(application))

    app.post_init = post_init

    print("🚀 ቦቱ ሙሉ ትንተና እና ዜና ማሳሰቢያ ሁነታ ስራ ጀምሯል...")
    app.run_polling()

if __name__ == '__main__':
    main()
