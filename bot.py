import telebot
import requests
import os
import re
import base64
from telebot import types
from gradio_client import Client, handle_file

# --- Bot Token နှင့် API Keys ---
BOT_TOKEN = "8832097622:AAGDRdS2MnUF9fIr_nObk7k_o-MrWxsCLzI"
GEMINI_API_KEY = "AQ.Ab8RN6KLWv7yaQbATbuEAiaFa-KFOX52kWov4X4N_nhxsclZQg"

# --- Hugging Face RVC Space အချက်အလက်များ ---
HF_SPACE_NAME = "RVC-Boss/GPT-SoVITS" 
HF_TOKEN = "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"

# --- ငွေလက်ခံမည့် အချက်အလက်များ ---
ALLOWED_NAME = "YeMinPhyo"
ALLOWED_PHONES = ["09759798544", "09773826118", "98544", "26118"]
ADMIN_CHAT_ID = 8640614876

CHAR_LIST = [1000, 2000, 4000, 5000, 8000, 10000, 20000, 40000, 50000, 80000, 100000]

PLANS = {
    "rvc": {
        "name": "🟢 1. Economy Plan (RVC)",
        "rate_per_1k": 500,  
        "subs": {
            "7d": {"title": "7 ရက်စာ Pass", "chars": "6,000", "price": 3000},
            "15d": {"title": "15 ရက်စာ Pass", "chars": "15,000", "price": 7000},
            "1m": {"title": "1 လစာ Pass", "chars": "35,000", "price": 16000},
            "2m": {"title": "2 လစာ Pass", "chars": "75,000", "price": 34000},
            "3m": {"title": "3 လစာ Pass", "chars": "120,000", "price": 50000},
            "5m": {"title": "5 လစာ Pass", "chars": "220,000", "price": 90000},
        }
    },
    "fish": {
        "name": "🔵 2. Standard Plan (Fish Audio)",
        "rate_per_1k": 1000, 
        "subs": {
            "7d": {"title": "7 ရက်စာ Pass", "chars": "6,000", "price": 5500},
            "15d": {"title": "15 ရက်စာ Pass", "chars": "15,000", "price": 13500},
            "1m": {"title": "1 လစာ Pass", "chars": "35,000", "price": 30000},
            "2m": {"title": "2 လစာ Pass", "chars": "75,000", "price": 65000},
            "3m": {"title": "3 လစာ Pass", "chars": "120,000", "price": 100000},
            "5m": {"title": "5 လစာ Pass", "chars": "220,000", "price": 180000},
        }
    },
    "eleven": {
        "name": "👑 3. VIP Premium Plan (ElevenLabs)",
        "rate_per_1k": 2500, 
        "subs": {
            "7d": {"title": "7 ရက်စာ Pass", "chars": "6,000", "price": 15000},
            "15d": {"title": "15 ရက်စာ Pass", "chars": "15,000", "price": 37500},
            "1m": {"title": "1 လစာ Pass", "chars": "35,000", "price": 87500},
            "2m": {"title": "2 လစာ Pass", "chars": "75,000", "price": 187500},
            "3m": {"title": "3 လစာ Pass", "chars": "120,000", "price": 300000},
            "5m": {"title": "5 လစာ Pass", "chars": "220,000", "price": 550000},
        }
    }
}

bot = telebot.TeleBot(BOT_TOKEN)
REF_FILE = "used_refs.txt"
user_states = {}

def load_used_refs():
    if os.path.exists(REF_FILE):
        with open(REF_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_ref(ref_no):
    with open(REF_FILE, "a") as f:
        f.write(f"{ref_no}\n")

# --- Admin များအတွက် စလစ်မလိုဘဲ တန်းစမ်းရန် Command ---
@bot.message_handler(commands=['test'])
def test_mode(message):
    user_id = message.chat.id
    user_states[user_id] = {'step': 'wait_audio_input', 'plan_key': 'rvc'}
    bot.reply_to(message, "👑 Admin Test Mode ပွင့်သွားပါပြီ ပန်းချယ်ရီမေ!\n\n🎙️ အသံပြောင်းလိုသော Voice Note သို့မဟုတ် Audio ဖိုင် တန်းပို့ပေးလို့ ရပါပြီခင်ဗျာ။")

@bot.message_handler(commands=['start', 'help', 'menu'])
def send_main_menu(message):
    user_id = message.chat.id
    user_states[user_id] = {'step': 'main_menu'}

    welcome_text = (
        "မင်္ဂလာပါ 👋 AI Voice & Video Cloning Bot မှ ကြိုဆိုပါသည် ပန်းချယ်ရီမေ!\n\n"
        "ကျေးဇူးပြု၍ အသုံးပြုလိုသော **AI Plan (၃) မျိုး** အနက်မှ တစ်ခုကို ရွေးချယ်ပေးပါ -"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    for p_key, p_val in PLANS.items():
        markup.add(types.InlineKeyboardButton(p_val["name"], callback_data=f"plan_{p_key}"))

    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("plan_"))
def handle_plan_choice(call):
    user_id = call.message.chat.id
    p_key = call.data.split("_")[1]
    plan = PLANS[p_key]

    user_states[user_id] = {'step': 'choose_buy_type', 'selected_plan': p_key}

    menu_text = (
        f"🎯 **{plan['name']}** ကို ရွေးချယ်ထားပါသည်!\n\n"
        "ဝယ်ယူလိုသော **အမျိုးအစား** ကို ရွေးချယ်ပေးပါ -"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📝 စာလုံးရေဖြင့် ဝယ်ယူရန်", callback_data=f"opt_char_{p_key}"),
        types.InlineKeyboardButton("📅 လစဉ်/ရက်အလိုက် ဝယ်ယူရန်", callback_data=f"opt_sub_{p_key}"),
        types.InlineKeyboardButton("⬅️ ပင်မ Menu သို့ ပြန်သွားရန်", callback_data="back_to_main")
    )

    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=menu_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("opt_char_"))
def show_char_buttons(call):
    user_id = call.message.chat.id
    p_key = call.data.split("_")[2]
    plan = PLANS[p_key]

    menu_text = f"📝 **{plan['name']} - စာလုံးရေအလိုက် ပက်ကေ့ချ်များ** -"
    markup = types.InlineKeyboardMarkup(row_width=1)
    for count in CHAR_LIST:
        price = int((count / 1000) * plan["rate_per_1k"])
        btn_text = f"🔹 စာလုံးရေ {count:,} လုံး - {price:,} ကျပ်"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buyc_{p_key}_{count}_{price}"))

    markup.add(types.InlineKeyboardButton("⬅️ နောက်သို့ ပြန်သွားရန်", callback_data=f"plan_{p_key}"))
    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=menu_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("opt_sub_"))
def show_sub_buttons(call):
    user_id = call.message.chat.id
    p_key = call.data.split("_")[2]
    plan = PLANS[p_key]

    menu_text = f"📅 **{plan['name']} - သက်တမ်းအလိုက် ပက်ကေ့ချ်များ** -"
    markup = types.InlineKeyboardMarkup(row_width=1)
    for sub_key, sub_val in plan["subs"].items():
        btn_text = f"👑 {sub_val['title']} ({sub_val['chars']} လုံး) - {sub_val['price']:,} ကျပ်"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buys_{p_key}_{sub_key}"))

    markup.add(types.InlineKeyboardButton("⬅️ နောက်သို့ ပြန်သွားရန်", callback_data=f"plan_{p_key}"))
    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=menu_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main(call):
    user_id = call.message.chat.id
    welcome_text = "ကျေးဇူးပြု၍ အသုံးပြုလိုသော **AI Plan (၃) မျိုး** အနက်မှ တစ်ခုကို ရွေးချယ်ပေးပါ -"
    markup = types.InlineKeyboardMarkup(row_width=1)
    for p_key, p_val in PLANS.items():
        markup.add(types.InlineKeyboardButton(p_val["name"], callback_data=f"plan_{p_key}"))
    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("buyc_") or call.data.startswith("buys_"))
def handle_package_selection(call):
    user_id = call.message.chat.id
    parts = call.data.split("_")
    
    if parts[0] == "buyc":
        p_key, count, price = parts[1], int(parts[2]), int(parts[3])
        desc = f"{PLANS[p_key]['name']} (စာလုံးရေ {count:,} လုံး)"
    else:
        p_key, sub_key = parts[1], parts[2]
        sub_info = PLANS[p_key]["subs"][sub_key]
        desc = f"{PLANS[p_key]['name']} - {sub_info['title']} ({sub_info['chars']} လုံး)"
        price = sub_info['price']

    user_states[user_id] = {'step': 'wait_slip', 'pack_desc': desc, 'price': price, 'plan_key': p_key}
    bot.answer_callback_query(call.id, "ရွေးချယ်ပြီးပါပြီ!")

    payment_msg = (
        f"💳 **ငွေပေးချေရန် အချက်အလက်များ**\n\n"
        f"• **ပက်ကေ့ချ်:** `{desc}`\n"
        f"• **ကျသင့်ငွေ:** `{price:,} ကျပ်`\n\n"
        "📌 **ငွေလွှဲရမည့် အကောင့်များ:**\n"
        "• **KBZ Pay:** `09759798544` (YeMinPhyo)\n"
        "• **Wave Pay:** `09773826118` (YeMinPhyo)\n\n"
        f"⚠️ ငွေလွှဲစလစ်ပုံကို ပို့ပေးပါ။"
    )
    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=payment_msg, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def handle_slip_photo(message):
    user_id = message.chat.id
    if user_id not in user_states or user_states[user_id].get('step') != 'wait_slip':
        bot.reply_to(message, "ကျေးဇူးပြု၍ /start နှိပ်ပြီး Package တစ်ခုခု ရွေးချယ်ပါ။")
        return

    state = user_states[user_id]
    expected_price = state['price']

    try:
        bot.reply_to(message, "စလစ်ပုံကို AI ဖြင့် စစ်ဆေးနေပါသည်။ ခဏ စောင့်ပေးပါ...")
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        prompt_text = (
            "ဒီပုံက မြန်မာနိုင်ငံက ငွေလွှဲစလစ် (KBZPay, KPay, WavePay စသည်) ဖြစ်ပါတယ်။ "
            "ပုံထဲမှ လုပ်ဆောင်မှုအမှတ် (Transaction ID / Ref No)၊ လက်ခံသူ၊ ငွေပမာဏ နှင့် ရက်စွဲ တို့ကို စစ်ဆေးပေးပါ။ "
            "ကျေးဇူးပြု၍ စာကြောင်းအစမှာ 'REF_NO: [နံပါတ်]' လို့ တိတိကျကျ ရေးပေးပါ။"
        )
        payload = {"contents": [{"parts": [{"text": prompt_text}, {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}}]}]}

        response = requests.post(url, json=payload, timeout=30)
        res_data = response.json()

        if "candidates" in res_data and len(res_data["candidates"]) > 0:
            reply_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            
            match_ref = re.search(r'(?:REF_NO|Transaction ID|လုပ်ဆောင်မှုအမှတ်)[:\s]*([A-Za-z0-9]+)', reply_text, re.IGNORECASE)
            ref_no = None

            if match_ref:
                ref_no = match_ref.group(1).strip()
            else:
                digits = re.findall(r'\b\d{10,20}\b', reply_text)
                if digits:
                    ref_no = digits[0]

            if ref_no:
                if ref_no in load_used_refs():
                    bot.reply_to(message, "❌ ဤစလစ်မှာ အသုံးပြုပြီးသား ဖြစ်နေပါသည်။")
                    return
                save_ref(ref_no)

            admin_msg = f"🟢 ငွေဝင်ရောက်မှု ({state['pack_desc']} - {expected_price:,} ကျပ်)\n\n{reply_text}"
            bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id, caption=admin_msg)

            state['step'] = 'wait_audio_input'
            thank_you_msg = (
                "🎉 **ငွေပေးချေမှု အောင်မြင်ပါသည်!**\n\n"
                "ကျွန်ုပ်တို့၏ AI Voice Changer ဝန်ဆောင်မှုကို ယုံကြည်စွာ ဝယ်ယူအားပေးသည့်အတွက် အထူးပင် ကျေးဇူးတင်ရှိပါသည်။\n\n"
                "🎙️ ယခု **အသံပြောင်းလိုသော အသံဖိုင် (Voice Note သို့မဟုတ် Audio)** ကို စတင်ပို့ပေးလို့ ရပါပြီခင်ဗျာ။"
            )
            bot.reply_to(message, thank_you_msg, parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ စလစ်ပုံထဲတွင် အချက်အလက်များ ရှာမတွေ့ပါ။ ငွေလွှဲစလစ်ပုံ အမှန်ကို ပို့ပေးပါခင်ဗျာ။")

    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio_input(message):
    user_id = message.chat.id
    if user_id not in user_states or user_states[user_id].get('step') != 'wait_audio_input':
        return

    state = user_states[user_id]
    bot.reply_to(message, "⚙️ Hugging Face RVC AI ဖြင့် အသံပြောင်းလဲနေပါသည် ခဏစောင့်ပါ...")

    try:
        file_info = bot.get_file(message.voice.file_id if message.voice else message.audio.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        input_audio_path = f"input_{user_id}.wav"
        with open(input_audio_path, 'wb') as f:
            f.write(downloaded_file)

        client = Client(HF_SPACE_NAME, hf_token=HF_TOKEN)
        
        result = client.predict(
            audio=handle_file(input_audio_path),
            api_name="/predict" 
        )

        output_audio_path = result if isinstance(result, str) else result[0]
        with open(output_audio_path, 'rb') as converted_audio:
            bot.send_voice(user_id, converted_audio, caption="🎤 အသံပြောင်းလဲပေးထားသော ဖိုင်ဖြစ်ပါတယ် ပန်းချယ်ရီမေ!")

        if os.path.exists(input_audio_path):
            os.remove(input_audio_path)

    except Exception as e:
        bot.reply_to(message, f"❌ အသံပြောင်းရာတွင် အမှားအယွင်းရှိပါသည်: {str(e)}")

if __name__ == '__main__':
    print("Bot start running...")
    bot.infinity_polling()
