# --- 2. Source Audio လက်ခံပြီး AI ဖြင့် အသံပြောင်းလဲခြင်း ---
@bot.message_handler(content_types=["voice", "audio"])
def handle_source_audio(message):
    user_id = message.chat.id
    state = user_states.get(user_id, {})
    target_audio_path = state.get("target_audio_path")

    if not target_audio_path or not os.path.exists(target_audio_path):
        bot.reply_to(message, "❌ ကျေးဇူးပြု၍ ပထမဦးစွာ Target Voice အသံဖိုင်ကို ပို့ပေးပါဦး။")
        return

    bot.reply_to(message, "⚙️ Hugging Face RVC AI ဖြင့် အသံနှစ်ခုကို ချိတ်ဆက်ကာ အသံပြောင်းလဲနေသည် ခဏစောင့်ပါ...")

    try:
        file_info = bot.get_file(message.voice.file_id if message.voice else message.audio.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        source_audio_path = f"source_{user_id}.wav"
        with open(source_audio_path, "wb") as f:
            f.write(downloaded_file)

        client = Client(HF_SPACE_NAME)

        # api_name မသုံးဘဲ fn_index=0 ဖြင့် အဆင်ပြေအောင် ချိတ်ဆက်ခြင်း
        try:
            prediction = client.predict(
                handle_file(target_audio_path),
                handle_file(source_audio_path),
                0,        # f0_up_key
                "pm",     # f0_method
                0.6,      # index_rate
                3,        # filter_radius
                0,        # resample_sr
                0.25,     # rms_mix_rate
                0.33,     # protect
                fn_index=0
            )
        except Exception:
            try:
                prediction = client.predict(
                    handle_file(target_audio_path),
                    handle_file(source_audio_path),
                    fn_index=0
                )
            except Exception:
                prediction = client.predict(
                    handle_file(target_audio_path),
                    handle_file(source_audio_path)
                )

        if isinstance(prediction, (list, tuple)):
            output_audio_path = prediction[0] if len(prediction) > 0 else None
        elif isinstance(prediction, dict):
            output_audio_path = list(prediction.values())[0] if prediction else None
        else:
            output_audio_path = str(prediction)

        if not output_audio_path or not os.path.exists(str(output_audio_path)):
            raise Exception("AI Space မှ အသံဖိုင် ထွက်မလာပါ")

        with open(output_audio_path, "rb") as converted_audio:
            bot.send_voice(user_id, converted_audio, caption="✅ **Custom Target Voice ဖြင့် အသံပြောင်းပြီးပါပြီ**")

        for p in [target_audio_path, source_audio_path]:
            if p and os.path.exists(p):
                os.remove(p)

    except Exception as e:
        bot.reply_to(message, f"❌ အသံပြောင်းရာတွင် အမှားဖြစ်သွားပါသည်: {str(e)}")

    user_states.pop(user_id, None)
