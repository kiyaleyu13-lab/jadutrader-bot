async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⏳ ትንተና እየተሰራ ነው...")

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # ፎቶውን በመጠን መቀነስ (ለፈጣን ጭነት እና ትንተና)
        image = Image.open(io.BytesIO(photo_bytes))
        image.thumbnail((1024, 1024))

        # የተስተካከለ እና አጭር ፕረምፕ (ለፈጣን ምላሽ)
        analysis_prompt = """
        Analyze this Forex/Crypto trading chart in Amharic:
        1. 📊 Trend & Market Structure (BOS, CHOCH)
        2. 🏦 SMC Elements (Order Blocks, FVG)
        3. 📉 Support & Resistance
        4. 🎯 Trade Setup (Bias, Entry, SL, TP)
        Keep it concise, professional, and entirely in Amharic.
        """

        response = ai_client.models.generate_content(
            model='gemini-3.8-flash',
            contents=[image, analysis_prompt]
        )

        await status_msg.edit_text(response.text)

    except Exception as e:
        logging.error(f"Error: {e}")
        await status_msg.edit_text(f"❌ ስህተት ተፈጥሯል: {str(e)}")

