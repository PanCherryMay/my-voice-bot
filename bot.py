import os
import re
import base64
import json
import requests
import threading
from flask import Flask
from telebot import types
import telebot
from gradio_client import Client, handle_file

# --- Render မှာ မအိပ်အောင် Flask Web Server တည်ဆောက်ခြင်း ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot is active and running 24/7!"

# --- Bot Token နှင့် API Keys (Environment Variables မှ ယူမည်) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- Hugging Face RVC Space အချက်အလက်များ ---
HF_SPACE_NAME = "r3gm/rvc_zero"

# --- ငွေလက်ခံမည့် အချက်အလက်များ ---
ALLOWED_NAME = "YeMinPhyo"
ALLOWED_PHONES = ["09759798544", "09773826118", "98544", "26118"]
ADMIN_CHAT_ID = 8640614876

REF_FILE = "used_refs.txt"
USER_DATA_FILE = "users_data.json"
user_states = {}

PLANS = {
    "rvc": {
        "name": "🟢 1. Economy Plan (RVC)",
        "rate_per_1k": 500,
        "subs": {
            "7d": {"title": "7 ရက်စာ Pass", "chars": "6,000", "price": 3000},
            "15d": {"title": "15 ရက်စာ Pass", "chars": "15,000", "price": 3000},
            "1m": {"title": "1 လစာ Pass", "chars": "35,000", "price": 5000},
            "2m": {"title": "2 လစာ Pass", "chars": "75,000", "price": 34000},
            "3m": {"title": "3 လစာ Pass", "chars": "120,000", "price": 50000},
            "5m": {"title": "5 လစာ Pass", "chars": "220,000", "price": 90000},
        },
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
        },
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
        },
    },
}

bot = telebot.TeleBot(BOT_TOKEN)

# --- ဒေတာဖတ်ရန်/သိမ်းရန် ဖန်ရှင်များ ---
def load_used_refs():
    if os.path.exists(REF_FILE):
        with open(REF_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_ref(ref_no):
    with open(REF_FILE, "a") as f:
        f.write(f"{ref_no}\n")

def load_users():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_users(data):
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# --- Admin Command: သုံးစွဲသူများစာရင်း ကြည့်ရန် ---
@bot.message_handler(commands=["users"])
def view_all_users(message):
    if message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "❌ ဤ Command ကို အသုံးပြုခွင့် မရှိပါ။")
        return

    users = load_users()
    if not users:
        bot.reply_to(message, "📭 လက်ရှိအချိန်အထိ ဝယ်ယူသုံးစွဲထားသော သုံးစွဲသူ မရှိသေးပါ။")
        return

    text = "👥 **ဝယ်ယူအသုံးပြုထားသူများစာရင်း:**\n\n"
    for uid, data in users.items():
        text += f"👤 အမည်: {data['name']} (@{data['username']})\n"
        text += f"🆔 ID: `{uid}`\n"
        text += f"📦 ဝယ်ယူထားမှုများ:\n"
        for p in data["packages"]:
            text += f"  • {p['package']} — {p['price']:,} ကျပ် [Ref: {p['ref']}]\n"
        text += "------------------------\n"

    if len(text) > 4000:
        for x in range(0, len(text), 4000):
            bot.send_message(ADMIN_CHAT_ID, text[x:x+4000], parse_mode="Markdown")
    else:
        bot.send_message(ADMIN_CHAT_ID, text, parse_mode="Markdown")


@bot.message_handler(commands=["start", "help", "menu"])
def send_main_menu(message):
    user_id = message.chat.id
    user_states[user_id] = {"step": "main_menu"}

    welcome_text = (
        "မင်္ဂလာပါရှင့် ✨\n\n"
        "🤖 AI Voice Services Bot မှ ကြိုဆိုပါတယ်ရှင့် 🌸\n\n"
        "🎙️ AI Voice Cloning ပြုလုပ်ရန်အတွက် Plan အမျိုးအစား (၃) မျိုး ခွဲခြားထားပါတယ်ရှင့် 💎\n\n"
        "Plan များကို အသုံးပြုရန်နှင့် အသေးစိတ်သိရှိနိုင်ရန်အတွက် အသုံးပြုလိုသော **AI Plan (၃) မျိုး** အနက်မှ တစ်ခုကို ရွေးချယ်ပေးပါ ရှင့် 👇"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    for p_key, p_val in PLANS.items():
        markup.add(types.InlineKeyboardButton(p_val["name"], callback_data=f"plan_{p_key}"))

    markup.add(types.InlineKeyboardButton("🔍 Plan သုံးမျိုးကို အသေးစိတ်လေ့လာရန် 💡", callback_data="view_plan_details"))

    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data == "view_plan_details")
def show_plan_details(call):
    user_id = call.message.chat.id

    details_text = (
        "📊 **AI Voice Services Plan များအကြောင်း အသေးစိတ်ရှင်းလင်းချက်** 💎\n\n"
        "🟢 **1. Economy Plan (RVC)**\n"
        "• **အကြောင်းအရာ:** စျေးနှုန်းအသက်သာဆုံးဖြစ်ပြီး အသံပြောင်းလဲခြင်း (Voice Conversion) ကို အခြေခံကျကျနှင့် အရည်အသွေးကောင်းမွန်စွာ ပြုလုပ်ပေးပါတယ်။\n\n"
        "🔵 **2. Standard Plan (Fish Audio)**\n"
        "• **အကြောင်းအရာ:** အသံထွက်ဆိုပုံနှင့် အသံအနိမ့်အမြင့်များကို ပိုမိုသဘာဝကျကျနှင့် ရှင်းလင်းပြတ်သားစွာ ထုတ်လုပ်ပေးပါတယ်။\n\n"
        "👑 **3. VIP Premium Plan (ElevenLabs)**\n"
        "• **အကြောင်းအရာ:** ကမ္ဘာ့အမြင့်မားဆုံး AI အသံနည်းပညာဖြစ်ပြီး လူသားတစ်ယောက်အတိုင်း စိတ်ခံစားချက်အပြည့်အဝဖြင့် အကောင်းဆုံး ထွက်ရှိစေပါတယ်။"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ ပင်မ Menu သို့ ပြန်သွားရန်", callback_data="back_to_main"))

    bot.edit_message_text(
        chat_id=user_id, message_id=call.message.message_id,
        text=details_text, reply_markup=markup, parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("plan_"))
def handle_plan_choice(call):
    user_id = call.message.chat.id
    p_key = call.data.split("_")[1]
    plan = PLANS[p_key]

    user_states[user_id] = {"step": "choose_buy_type", "selected_plan": p_key}

    menu_text = (
        f"🎯 **{plan['name']}** ကို ရွေးချယ်ထားပါသည် ✨\n\n"
        f"ဝယ်ယူလိုသော **အမျိုးအစား** ကို ရွေးချယ်ပေးပါရှင့် 🌸 👇"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⏳ 15 ရက်စာ Pass (3,000 ကျပ်)", callback_data=f"buys_{p_key}_15d"),
        types.InlineKeyboardButton("⭐ 1 လစာ Pass (5,000 ကျပ်)", callback_data=f"buys_{p_key}_1m"),
        types.InlineKeyboardButton("⬅️ ပင်မ Menu သို့ ပြန်သွားရန်", callback_data="back_to_main"),
    )

    bot.edit_message_text(
        chat_id=user_id, message_id=call.message.message_id,
        text=menu_text, reply_markup=markup, parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main(call):
    user_id = call.message.chat.id
    user_states[user_id] = {"step": "main_menu"}

    welcome_text = (
        "မင်္ဂလာပါရှင့် ✨\n\n"
        "🤖 AI Voice Services Bot မှ ကြိုဆိုပါတယ်ရှင့် 🌸\n\n"
        "🎙️ AI Voice Cloning ပြုလုပ်ရန်အတွက် Plan အမျိုးအစား (၃) မျိုး ခွဲခြားထားပါတယ်ရှင့် 💎\n\n"
        "Plan များကို အသုံးပြုရန်နှင့် အသေးစိတ်သိရှိနိုင်ရန်အတွက် အသုံးပြုလိုသော **AI Plan (၃) မျိုး** အနက်မှ တစ်ခုကို ရွေးချယ်ပေးပါ ရှင့် 👇"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    for p_key, p_val in PLANS.items():
        markup.add(types.InlineKeyboardButton(p_val["name"], callback_data=f"plan_{p_key}"))

    markup.add(types.InlineKeyboardButton("🔍 Plan သုံးမျိုးကို အသေးစိတ်လေ့လာရန် 💡", callback_data="view_plan_details"))

    try:
        bot.edit_message_text(
            chat_id=user_id, message_id=call.message.message_id,
            text=welcome_text, reply_markup=markup, parse_mode="Markdown"
        )
    except Exception:
        bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")


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
        price = sub_info["price"]

    # --- 👑 ADMIN FREE BYPASS (စလစ်မလိုဘဲ တိုက်ရိုက်သုံးရန်) ---
    if user_id == ADMIN_CHAT_ID:
        user_states[user_id] = {
            "step": "wait_target_audio",
            "pack_desc": desc,
            "price": 0,
            "plan_key": p_key,
        }
        bot.answer_callback_query(call.id, "Admin Free Access ခွင့်ပြုထားပါသည်!")

        admin_free_msg = (
            f"👑 **Admin အထူးအခွင့်အရေး (Free Access)**\n\n"
            f"• **ရွေးချယ်ထားသည့် Plan:** `{desc}`\n"
            f"• **ကျသင့်ငွေ:** `0 ကျပ် (Admin Free)`\n\n"
            "✨ ငွေလွှဲစလစ် မလိုအပ်ပါ။\n"
            "🎙️ **အဆင့် (၁):** ပထမဦးစွာ **ပြောင်းချင်သည့် ပုံစံတူ အသံဖိုင် (Target Voice Sample)** ကို အရင် ပို့ပေးပါခင်ဗျာ။"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 ပင်မမီနူးသို့ ပြန်သွားရန်", callback_data="back_to_main"))

        bot.edit_message_text(
            chat_id=user_id, message_id=call.message.message_id,
            text=admin_free_msg, reply_markup=markup, parse_mode="Markdown"
        )
        return
    # --------------------------------------------------------

    user_states[user_id] = {
        "step": "wait_slip",
        "pack_desc": desc,
        "price": price,
        "plan_key": p_key,
    }
    bot.answer_callback_query(call.id, "ရွေးချယ်ပြီးပါပြီ!")

    payment_msg = (
        f"💳 **ငွေပေးချေရန် အချက်အလက်များ**\n\n"
        f"• **ပက်ကေ့ချ်:** `{desc}`\n"
        f"• **ကျသင့်ငွေ:** `{price:,} ကျပ်`\n\n"
        "📌 **ငွေလွှဲရမည့် အကောင့်များ:**\n"
        "• **KBZ Pay:** `09759798544` (YeMinPhyo)\n"
        "• **Wave Pay:** `09773826118` (YeMinPhyo)\n\n"
        "⚠️ ငွေလွှဲစလစ်ပုံကို ပို့ပေးပါ။"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 ပင်မမီနူးသို့ ပြန်သွားရန်", callback_data="back_to_main"))

    bot.edit_message_text(
        chat_id=user_id, message_id=call.message.message_id,
        text=payment_msg, reply_markup=markup, parse_mode="Markdown"
    )


@bot.message_handler(content_types=["photo"])
def handle_slip_photo(message):
    user_id = message.chat.id
    if user_id not in user_states or user_states[user_id].get("step") != "wait_slip":
        bot.reply_to(message, "ကျေးဇူးပြု၍ /start နှိပ်ပြီး Package တစ်ခုခု ရွေးချယ်ပါ။")
        return

    state = user_states[user_id]
    expected_price = state["price"]

    try:
        bot.reply_to(message, "စလစ်ပုံကို AI ဖြင့် စစ်ဆေးနေပါသည်။ ခဏ စောင့်ပေးပါ...")
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(downloaded_file).decode("utf-8")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

        prompt_text = (
            "ဒီပုံသည် ငွေလွှဲပြေစာ (Payment Slip) ဟုတ်မဟုတ် သေချာစစ်ဆေးပါ။\n"
            "အကယ်၍ ငွေလွှဲပြေစာ မဟုတ်လျှင် (သို့မဟုတ်) ဖုန်းစခရင်ရှော့ (Screenshot) သို့မဟုတ် အခြားပုံများ ဖြစ်နေလျှင် REF_NO, လက်ခံသူ, ငွေပမာဏ နေရာများတွင် N/A ဟုသာ ဖော်ပြပါအချက်အလက်များကို အောက်ပါအတိုင်း တိတိကျကျ ထုတ်ပေးပါ -\n"
            "REF_NO: (လုပ်ငန်းစဉ်အမှတ် ဥပမာ- 01004252021761786962 ကို ဖော်ပြပါ၊ မရှိလျှင် N/A)\n"
            "လက်ခံသူ: (ငွေလက်ခံသူအမည် သို့မဟုတ် ဖုန်းနံပါတ်ကို ဖော်ပြပါ၊ မရှိလျှင် N/A)\n"
            "ငွေပမာဏ: (ငွေပမာဏကို နံပါတ်သီးသန့် ဖော်ပြပါ၊ မရှိလျှင် N/A)"
        )

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt_text},
                    {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}},
                ]
            }],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }

        response = requests.post(url, json=payload, timeout=30)
        res_data = response.json()

        if "candidates" in res_data and len(res_data["candidates"]) > 0:
            candidate = res_data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                reply_text = candidate["content"]["parts"][0]["text"]

                match_ref = re.search(r"REF_NO:\s*([A-Za-z0-9]+)", reply_text)
                match_receiver = re.search(r"လက်ခံသူ:\s*(.*)", reply_text)
                match_amount = re.search(r"ငွေပမာဏ:\s*([0-9,]+)", reply_text)

                ref_val = match_ref.group(1).strip() if match_ref else "N/A"
                receiver_val = match_receiver.group(1).strip() if match_receiver else "N/A"

                amount_str = match_amount.group(1).replace(",", "").replace("-", "").strip() if match_amount else "0"
                amount_val = int(amount_str) if amount_str.isdigit() else 0

                if ref_val == "N/A" or receiver_val == "N/A" or amount_val == 0:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("🔄 ပင်မမီနူးသို့ ပြန်သွားရန်", callback_data="back_to_main"))
                    bot.reply_to(message, "❌ **ငွေပေးချေမှု မအောင်မြင်ပါ!** ပေးပို့လာသော ပုံသည် မှန်ကန်သည့် ငွေလွှဲပြေစာ မဟုတ်ပါ။", reply_markup=markup)
                    return

                if ALLOWED_NAME.lower() not in receiver_val.lower():
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("🔄 ပင်မမီနူးသို့ ပြန်သွားရန်", callback_data="back_to_main"))
                    bot.reply_to(message, f"❌ **ငွေပေးချေမှု မအောင်မြင်ပါ!** လက်ခံသူအမည် (`{receiver_val}`) မမှန်ကန်ပါ။", reply_markup=markup)
                    return

                if amount_val != expected_price:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("🔄 ပင်မမီနူးသို့ ပြန်သွားရန်", callback_data="back_to_main"))
                    bot.reply_to(message, f"❌ **ငွေပေးချေမှု မအောင်မြင်ပါ!** ငွေပမာဏ (`{amount_val:,} ကျပ်`) လွဲမှားနေပါသည်။", reply_markup=markup)
                    return

                if ref_val in load_used_refs():
                    bot.reply_to(message, "❌ ဤစလစ်မှာ အသုံးပြုပြီးသား (စလစ်အဟောင်း) ဖြစ်နေပါသည်။")
                    return

                save_ref(ref_val)

                users = load_users()
                str_user_id = str(user_id)
                if str_user_id not in users:
                    users[str_user_id] = {
                        "username": message.from_user.username or "No Username",
                        "name": message.from_user.first_name,
                        "packages": []
                    }

                users[str_user_id]["packages"].append({
                    "package": state['pack_desc'],
                    "price": expected_price,
                    "ref": ref_val
                })
                save_users(users)

                admin_msg = f"🟢 ငွေဝင်ရောက်မှု ({state['pack_desc']} - {expected_price:,} ကျပ်)\n\n{reply_text}"
                bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id, caption=admin_msg)

                state["step"] = "wait_target_audio"
                bot.reply_to(message, "🎉 ငွေပေးချေမှု အောင်မြင်ပါသည်!\n\n🎙️ **အဆင့် (၁):** ပထမဦးစွာ **ပြောင်းချင်သည့် ပုံစံတူ အသံဖိုင် (Target Voice Sample)** ကို အရင် ပို့ပေးပါခင်ဗျာ။")
                return

        error_reason = res_data.get("error", {}).get("message", "Unknown API error")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 ပင်မမီနူးသို့ ပြန်သွားရန်", callback_data="back_to_main"))
        bot.reply_to(message, f"❌ ပုံကို AI မှ စစ်ဆေး၍မရပါ။ (Error: {error_reason})", reply_markup=markup)

    except Exception as e:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 ပင်မမီနူးသို့ ပြန်သွားရန်", callback_data="back_to_main"))
        bot.reply_to(message, f"❌ Error ဖြစ်သွားပါသည်: {str(e)}", reply_markup=markup)


# --- 1. Target Voice အသံဖိုင် လက်ခံခြင်း ---
@bot.message_handler(content_types=["voice", "audio"], func=lambda message: message.chat.id in user_states and user_states[message.chat.id].get("step") == "wait_target_audio")
def handle_target_audio(message):
    user_id = message.chat.id
    state = user_states[user_id]

    try:
        file_info = bot.get_file(message.voice.file_id if message.voice else message.audio.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        target_audio_path = f"target_{user_id}.wav"
        with open(target_audio_path, "wb") as f:
            f.write(downloaded_file)

        state["target_audio_path"] = target_audio_path
        state["step"] = "wait_source_audio"

        bot.reply_to(message, "✅ **Target Voice လက်ခံရရှိပါပြီ။**\n\n🎙️ **အဆင့် (၂):** ယခု **အသံပြောင်းလိုသော သင့်ရဲ့ မူလအသံဖိုင် (Source Audio / Voice Note)** ကို ဆက်လက် ပို့ပေးပါခင်ဗျာ။")

    except Exception as e:
        bot.reply_to(message, f"❌ Target အသံဖိုင် သိမ်းဆည်းရာတွင် အမှားဖြစ်သွားပါသည်: {str(e)}")


# --- 2. Source Audio လက်ခံပြီး AI ဖြင့် အသံပြောင်းလဲခြင်း (အမှားပြင်ဆင်ပြီး) ---
@bot.message_handler(content_types=["voice", "audio"])
def handle_source_audio(message):
    user_id = message.chat.id
    state = user_states.get(user_id, {})
    target_audio_path = state.get("target_audio_path")

    if not target_audio_path or not os.path.exists(target_audio_path):
        bot.reply_to(message, "❌ ကျေးဇူးပြု၍ ပထမဦးစွာ /start နှိပ်၍ Step (1) Target Voice အသံဖိုင်ကို အရင် ပို့ပေးပါဦး။")
        return

    status_msg = bot.reply_to(message, "⚙️ Hugging Face RVC AI ဖြင့် အသံနှစ်ခုကို ချိတ်ဆက်ကာ အသံပြောင်းလဲနေသည် ခဏစောင့်ပါ...")

    source_audio_path = f"source_{user_id}.wav"
    try:
        file_info = bot.get_file(message.voice.file_id if message.voice else message.audio.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with open(source_audio_path, "wb") as f:
            f.write(downloaded_file)

        client = Client(HF_SPACE_NAME)

        prediction = None
        # Hugging Face Space ချိတ်ဆက်ခြင်းနှင့် ရလဒ်ယူခြင်း
        try:
            prediction = client.predict(
                handle_file(target_audio_path),
                handle_file(source_audio_path),
                0,        # pitch shift
                "pm",     # f0 method
                0.6,      # index rate
                3,        # filter radius
                0,        # resample sr
                0.25,     # rms mix rate
                0.33,     # protect
                fn_index=0
            )
        except Exception as e_first:
            # Fallback handling
            try:
                prediction = client.predict(
                    handle_file(target_audio_path),
                    handle_file(source_audio_path),
                    fn_index=0
                )
            except Exception as e_second:
                raise Exception("Hugging Face Server Busy ဖြစ်နေပါသဖြင့် ရလဒ်မထွက်ပါ။ ခဏစောင့်ပြီး ပြန်လည်စမ်းသပ်ပေးပါ။")

        # Result Parsing ဖြင့် Exception မတက်အောင် စစ်ဆေးခြင်း
        output_audio_path = None

        if isinstance(prediction, (list, tuple)) and len(prediction) > 0:
            output_audio_path = prediction[0]
        elif isinstance(prediction, dict) and len(prediction) > 0:
            output_audio_path = list(prediction.values())[0]
        elif isinstance(prediction, str) and prediction.strip():
            output_audio_path = prediction

        if not output_audio_path or not os.path.exists(str(output_audio_path)):
            raise Exception("AI Space မှ အသံဖိုင် ရလဒ် ထွက်မလာပါ သို့မဟုတ် Server တန့်သွားပါသည်။")

        with open(output_audio_path, "rb") as converted_audio:
            bot.send_voice(user_id, converted_audio, caption="✅ **Custom Target Voice ဖြင့် အသံပြောင်းပြီးပါပြီ**")

    except IndexError:
        bot.reply_to(message, "❌ **အသံပြောင်းရာတွင် အမှားဖြစ်သွားပါသည်။**\n(Hugging Face Space မှ GPU Server Busy ဖြစ်နေပါသဖြင့် ရလဒ် မထုတ်ပေးနိုင်ပါ။ မိနစ်အနည်းငယ်စောင့်ပြီး ပြန်လည်စမ်းသပ်ပေးပါခင်ဗျာ။)")
    except Exception as e:
        bot.reply_to(message, f"❌ အသံပြောင်းရာတွင် အမှားဖြစ်သွားပါသည်: {str(e)}")

    finally:
        # ယာယီသိမ်းထားသော Audio ဖိုင်များကို ဖျက်ဆီးခြင်း
        for p in [target_audio_path, source_audio_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
        user_states.pop(user_id, None)


# --- Bot ကို Thread နဲ့ Run ပြီး Flask ကို Main Thread မှာထားရန် ---
def run_bot():
    print("Telegram Bot is running...")
    bot.infinity_polling()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
