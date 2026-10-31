async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⏳ የChart ፎቶህን እየተነተንኩ ነው... እባክህ ትንሽ ጠብቀኝ...")

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # ፎቶውን በመጠን መቀነስ (ለፈጣን ጭነት እና ትንተና)
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

        # ሪስፖንሱን በትክክል መግለጽ
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
