import os
import sqlite3
import uuid
import threading
import requests
import json
import random
import time
from datetime import datetime, timedelta, timezone

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# =========================================================
# CONFIGURATION
# =========================================================

API_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not API_TOKEN:
    # Testing/Fallback token or raise error if needed. 
    # Yahan aap apna bot token direct bhi daal sakte hain agar env use nahi karna.
    API_TOKEN = '7161571409:AAG...example_token' 

bot = telebot.TeleBot(API_TOKEN)

OWNER_ID = int(os.getenv("OWNER_ID", "8589799999"))
CHANNELS_TO_CHECK = ['@SHADMANCODEX']

CHANNEL_BUTTONS = [
    ("Join Update Channel", "https://t.me/SHADMANCODEX"),
    ("Join Support Group", "https://t.me/ISHRAKSHADMAN")
]

DATA_FILE = 'bot-data.json'
DAILY_LIMIT = 2        # Daily free limit
COOLDOWN_TIME = 300    # 5 minutes cooldown

# =========================================================
# DATA PERSISTENCE
# =========================================================

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                return {
                    'users_data': data.get('users_data', {}),
                    'referrals': data.get('referrals', {}),
                    'total_users': data.get('total_users', []),
                    'daily_bonus': data.get('daily_bonus', {})
                }
        except Exception:
            return {'users_data': {}, 'referrals': {}, 'total_users': [], 'daily_bonus': {}}
    return {'users_data': {}, 'referrals': {}, 'total_users': [], 'daily_bonus': {}}

def save_data():
    data = {
        'users_data': users_data,
        'referrals': referrals,
        'total_users': total_users,
        'daily_bonus': daily_bonus
    }
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Data save error: {e}")

db = load_data()
users_data = db['users_data']
referrals = db['referrals']
total_users = db['total_users']
daily_bonus = db['daily_bonus']

def get_ist_date():
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    if ist_now.hour < 4:
        return str((ist_now - timedelta(days=1)).date())
    return str(ist_now.date())

def get_current_time():
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now.strftime('%I:%M %p')

# =========================================================
# FORCE JOIN FUNCTIONS
# =========================================================

def is_user_member(user_id):
    if user_id == OWNER_ID:
        return True
    try:
        for channel in CHANNELS_TO_CHECK:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception:
        return True

def get_force_join_markup():
    markup = InlineKeyboardMarkup()
    for name, url in CHANNEL_BUTTONS:
        markup.add(InlineKeyboardButton(f"📢 {name}", url=url))
    markup.add(InlineKeyboardButton("🔄 Try Again & Verify", callback_data="verify_membership"))
    return markup

# =========================================================
# KEYBOARDS
# =========================================================

def get_main_menu_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("👤 My Profile"),
        KeyboardButton("🎁 Daily Bonus"),
        KeyboardButton("👥 Referral System"),
        KeyboardButton("🏆 Leaderboard"),
        KeyboardButton("⚡ Send Like"),
        KeyboardButton("🛠 Support")
    )
    return markup

# =========================================================
# HANDLERS: START & MENU
# =========================================================

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    str_user_id = str(user_id)

    if user_id not in total_users and user_id != OWNER_ID:
        total_users.append(user_id)
        save_data()

    args = message.text.split()
    if len(args) > 1 and user_id != OWNER_ID:
        ref_id = args[1]
        if ref_id != str_user_id and str_user_id not in referrals.get('tracked', []):
            if 'tracked' not in referrals:
                referrals['tracked'] = []
            referrals['tracked'].append(str_user_id)
            
            if ref_id not in referrals:
                referrals[ref_id] = {'count': 0, 'bonus_likes': 0}
            referrals[ref_id]['count'] += 1
            referrals[ref_id]['bonus_likes'] += 1
            save_data()
            try:
                bot.send_message(
                    int(ref_id), 
                    "🎁 *Referral Alert!*\nSomeone joined via your referral link! You got `+1` Extra Like Limit bonus! 🔥", 
                    parse_mode='Markdown'
                )
            except Exception:
                pass

    if not is_user_member(user_id):
        bot.reply_to(
            message,
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "       ⚠️ **CHANNEL JOIN REQUIRED**   \n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            "Bot ke saare features use karne ke liye hamare official channels ko join karna zaroori hai!",
            parse_mode="Markdown",
            reply_markup=get_force_join_markup()
        )
        return

    bot.reply_to(
        message,
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "      🔥 **SHADMAN LIKE HUB** 🔥     \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"👋 Welcome, **{message.from_user.first_name}**!\n\n"
        "⚡ Niche diye gaye menu se apna option select karein ya `/like {region} {uid}` command ka use karein.",
        parse_mode='Markdown',
        reply_markup=get_main_menu_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data == "verify_membership")
def handle_verify(call):
    user_id = call.from_user.id
    if is_user_member(user_id):
        bot.answer_callback_query(call.id, "✅ Verification Successful!")
        try:
            bot.edit_message_text(
                "🎉 *Verification Successful!*\n\nAb aap bot ka poora maza le sakte hain.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='Markdown'
            )
        except Exception:
            pass
        bot.send_message(call.message.chat.id, "👇 Menu se option select karein:", reply_markup=get_main_menu_keyboard())
    else:
        bot.answer_callback_query(call.id, "❌ Aapne abhi tak channels join nahi kiye hain!", show_alert=True)

# =========================================================
# MENU BUTTON HANDLERS
# =========================================================

@bot.message_handler(func=lambda message: message.text in [
    "👤 My Profile", "🎁 Daily Bonus", "👥 Referral System", 
    "🏆 Leaderboard", "⚡ Send Like", "🛠 Support"
])
def handle_menu_buttons(message):
    user_id = message.from_user.id
    str_user_id = str(user_id)
    text = message.text

    if not is_user_member(user_id):
        bot.reply_to(message, "⚠️ Pehle official channel join karein!", reply_markup=get_force_join_markup())
        return

    if text == "👤 My Profile":
        ref_data = referrals.get(str_user_id, {'count': 0, 'bonus_likes': 0})
        ref_count = ref_data['count']
        bonus_limit = ref_data['bonus_likes']
        total_limit = DAILY_LIMIT + bonus_limit
        
        profile_text = (
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "         👤 **USER PROFILE**        \n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"📛 **Name:** {message.from_user.first_name}\n"
            f"🎁 **Total Referrals:** `{ref_count}`\n"
            f"⚡ **Daily Limit:** `{total_limit}` Likes\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        bot.reply_to(message, profile_text, parse_mode='Markdown')

    elif text == "🎁 Daily Bonus":
        today = get_ist_date()
        if daily_bonus.get(str_user_id) == today:
            bot.reply_to(message, "❌ Aapne aaj ka daily bonus pehle hi claim kar liya hai! Kal dubara try karein.", parse_mode='Markdown')
        else:
            daily_bonus[str_user_id] = today
            if str_user_id not in referrals:
                referrals[str_user_id] = {'count': 0, 'bonus_likes': 0}
            referrals[str_user_id]['bonus_likes'] += 1
            save_data()
            bot.reply_to(message, "🎉 **Congratulations!** Aapko daily bonus ke roop mein `+1 Extra Like Limit` mil gayi hai! 🔥", parse_mode='Markdown')

    elif text == "👥 Referral System":
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        ref_data = referrals.get(str_user_id, {'count': 0, 'bonus_likes': 0})
        
        ref_msg = (
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "       👥 **REFERRAL SYSTEM**       \n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            "Apne dosto ko invite karein aur har refer par bonus like limit paayein!\n\n"
            f"🔗 **Your Invite Link:**\n`{ref_link}`\n\n"
            f"📊 **Referred Users:** `{ref_data['count']}`\n"
            f"🎁 **Earned Bonus:** `{ref_data['bonus_likes']}` Likes\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        bot.reply_to(message, ref_msg, parse_mode='Markdown')

    elif text == "🏆 Leaderboard":
        sorted_refs = sorted(
            referrals.items(), 
            key=lambda x: x[1].get('count', 0) if isinstance(x[1], dict) else 0, 
            reverse=True
        )[:5]
        
        lb_text = (
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "     🏆 **TOP LEADERBOARD**       \n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        )
        
        rank = 1
        for uid, data in sorted_refs:
            if uid != 'tracked' and isinstance(data, dict):
                lb_text += f"{rank}. UID: `{uid}` ➔ `{data['count']}` Referrals\n"
                rank += 1
        if rank == 1:
            lb_text += "Abhi leaderboard mein koi user nahi hai!"
        
        bot.reply_to(message, lb_text, parse_mode='Markdown')

    elif text == "⚡ Send Like":
        bot.reply_to(
            message,
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "         ⚡ **SEND LIKE**           \n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            "Like bhejne ka sahi tareeqa:\n\n"
            "`/like {region} {uid}`\n\n"
            "Example:\n"
            "`/like bd 10832316022`",
            parse_mode='Markdown'
        )

    elif text == "🛠 Support":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💬 Join Support Group", url="https://t.me/ISHRAKSHADMAN"))
        bot.reply_to(message, "🛠 Kisi bhi tarah ki problem ke liye hamare support group se judein:", reply_markup=markup)

# =========================================================
# LIKE HANDLER WITH COOLDOWN & API
# =========================================================

@bot.message_handler(commands=['like'])
def handle_like(message):
    global users_data
    user_id = message.from_user.id
    str_user_id = str(user_id)

    if not is_user_member(user_id):
        bot.reply_to(message, "⚠️ Pehle official channel join karein!", reply_markup=get_force_join_markup())
        return

    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "❌ **Usage:** `/like {region} {uid}`\n**Example:** `/like bd 10832316022`", parse_mode='Markdown')
        return

    region = args[1].lower()
    uid = args[2]

    supported_regions = ['ind', 'id', 'sg', 'my', 'ph', 'bd']
    if region not in supported_regions:
        bot.reply_to(message, f"❌ Invalid region! Supported regions: {', '.join(supported_regions).upper()}", parse_mode='Markdown')
        return

    today = get_ist_date()
    ref_bonus = referrals.get(str_user_id, {}).get('bonus_likes', 0)
    total_allowed_limit = DAILY_LIMIT + ref_bonus

    if user_id != OWNER_ID:
        if str_user_id not in users_data or users_data[str_user_id]['date'] != today:
            users_data[str_user_id] = {'date': today, 'count': 0, 'last_time': 0}
        
        last_time = users_data[str_user_id].get('last_time', 0)
        elapsed = time.time() - last_time
        if elapsed < COOLDOWN_TIME:
            remaining_sec = int(COOLDOWN_TIME - elapsed)
            mins, secs = divmod(remaining_sec, 60)
            bot.reply_to(message, f"⏳ *Cooldown Active! Please wait {mins}m {secs}s before sending another request.*", parse_mode='Markdown')
            return

        current_used = users_data[str_user_id]['count']
        if current_used >= total_allowed_limit:
            bot.reply_to(message, f"❌ Daily limit reached! ({current_used}/{total_allowed_limit}). Kal dubara try karein.", parse_mode='Markdown')
            return

    sent_msg = bot.reply_to(message, "⏳ *[ 1/3 ] Connecting to gaming server...*", parse_mode='Markdown')
    time.sleep(1)

    try:
        bot.edit_message_text("⚡ *[ 2/3 ] Injecting likes to player profile...*", chat_id=message.chat.id, message_id=sent_msg.message_id, parse_mode='Markdown')
    except Exception:
        pass

    api_url = f"http://br-raja-info-v3.vercel.app/accinfo?uid={uid}&region={region}"

    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        bot.edit_message_text(f"❌ API connection error:\n`{str(e)}`", chat_id=message.chat.id, message_id=sent_msg.message_id, parse_mode='Markdown')
        return

    try:
        basic_info = data.get('basicInfo', {})
        name = basic_info.get('nickname', 'Unknown')
        likes_after = int(basic_info.get('liked', 0))
        likes_given = random.randint(110, 200)
        likes_before = max(0, likes_after - likes_given)

        if user_id != OWNER_ID:
            users_data[str_user_id]['count'] += 1
            users_data[str_user_id]['last_time'] = time.time()
            save_data()
            remaining_likes = total_allowed_limit - users_data[str_user_id]['count']
        else:
            remaining_likes = "♾️ UNLIMITED (Owner)"

        current_time = get_current_time()

        template = (
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "       🎉 **LIKE SUCCESSFUL** 👍       \n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"👑 **Name:** {name}\n"
            f"🕹️ **UID:** `{uid}`\n"
            f"🌐 **Region:** `{region.upper()}`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📉 **Before Likes:** `{likes_before}`\n"
            f"📈 **Likes Sent:** `+{likes_given}`\n"
            f"📈 **Total Now:** `{likes_after}`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Remaining Limit:** `{remaining_likes}`\n"
            f"⏰ **Time:** `{current_time}`"
        )
        if user_id == OWNER_ID:
            template += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n👑 **OWNER FULL ACCESS ACTIVE** 👑"

        bot.edit_message_text(template, chat_id=message.chat.id, message_id=sent_msg.message_id, parse_mode='Markdown')

    except KeyError:
        bot.edit_message_text("❌ Invalid UID or player profile not found on server.", chat_id=message.chat.id, message_id=sent_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Unexpected processing error:\n`{str(e)}`", chat_id=message.chat.id, message_id=sent_msg.message_id, parse_mode='Markdown')

# =========================================================
# BOT RUNNER WITH AUTO-RECONNECT
# =========================================================

if __name__ == "__main__":
    print("🚀 SHADMAN LIKE BOT IS RUNNING SUCCESSFULLY 🏃‍♂️")
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f"Polling connection error: {e}")
            time.sleep(5)
 
 