import os
from flask import Flask
from threading import Thread
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

TOKEN = '8878169821:AAGhdWcw59bFTVSFpxL0IALUpdIOkJBQAHU'
ADMIN_ID = 7161571409

bot = telebot.TeleBot(TOKEN)

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# Channels list with unique numeric or string channel ids (Use your channel username or ID starting with @)
CHANNELS = [
    {"name": "Proof Channel", "username": "@botlikeproof", "url": "https://t.me/botlikeproof"},
    {"name": "Earning Channel 1", "username": "@eraningwithask", "url": "https://t.me/eraningwithask"},
    {"name": "Earning Channel 2", "username": "@eraningwithask9", "url": "https://t.me/eraningwithask9"}
]

USERS = {}
PURCHASE_HISTORY = []
ADMIN_STATE = {}
USER_STATE = {}

SETTINGS = {
    'refer_reward': 5.0
}

CC_PLANS = {
    'plan_100': {
        "name": "💳 **PLAN 1**", 
        "price": "100", 
        "display_price": "₹100", 
        "value": "3K Value",
        "details": "```\n|           P R I M E   V I S A         |\n|___________|\n|                                       |\n|  HOLDER : horiyo soli                   |\n|  STATE  : Delhi                       |\n|                                       |\n|  CARD   : 4100 2800 0000 1007         |\n|  VALID  : 06 / 30                     |\n|  CVV    : 635                         |\n|___________|\n```"
    },
    'plan_199': {
        "name": "💳 **PLAN 2**", 
        "price": "199", 
        "display_price": "₹199", 
        "value": "6.5K Value",
        "details": "```\n╔═══════════ PRIME CARD 2 ════════════════╗\n║                                       ║\n║  HOLDER : MITOY DOWL                  ║\n║  STATE  : Delhi                       ║\n║                                       ║\nCARD   : 8176 0631 5600 4748                                  ║\n║  VALID  : 07 / 32                     ║\n║  CVV    : 917                         ║\n║                                       ║\n╚═══════════════════════════════════════╝\n```"
    },
    'plan_599': {
        "name": "💳 **PLAN 3**", 
        "price": "599", 
        "display_price": "₹599", 
        "value": "26K Value",
        "details": "```\n|           P R I M E   V I S A         |\n|___________|\n|                                       |\n|  HOLDER : horiyo soli                   |\n|  STATE  : Delhi                       |\n|                                       |\n|  CARD   : 4100 2800 0000 1007         |\n|  VALID  : 06 / 30                     |\n|  CVV    : 635                         |\n|___________|\n```"
    }
}

LIKE_PLANS = {
    'like_60': {
        "name": "❤️ **LIKE PACK 1**",
        "price": "60",
        "display_price": "₹60",
        "days": 15,
        "daily": 220,
        "total": 3300,
        "details": "❤️ **220 Likes Daily**\n📅 **Duration:** 15 Days\n🔥 **Total:** 3,300 Likes"
    },
    'like_120': {
        "name": "❤️ **LIKE PACK 2**",
        "price": "120",
        "display_price": "₹120",
        "days": 30,
        "daily": 220,
        "total": 6600,
        "details": "❤️ **220 Likes Daily**\n📅 **Duration:** 30 Days\n🔥 **Total:** 6,600 Likes"
    }
}

def main_reply_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("🛒 CC Store"),
        KeyboardButton("❤️ Like Store"),
        KeyboardButton("👛 My Wallet"),
        KeyboardButton("➕ Add Money"),
        KeyboardButton("👥 Refer & Earn"),
        KeyboardButton("🛠️ Support"),
        KeyboardButton("📦 My Active Plans")
    )
    if user_id == ADMIN_ID:
        markup.add(KeyboardButton("👑 Admin Panel"))
    return markup

def check_subscription(user_id):
    # Skips check for admin
    if user_id == ADMIN_ID:
        return True
    
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch['username'], user_id)
            if member.status not in ['creator', 'administrator', 'member']:
                return False
        except Exception as e:
            print(f"Error checking channel {ch['username']}: {e}")
            # Agar bot khud channel ka admin nahi hai, toh false return karega taaki user join karne par force ho
            return False
    return True

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    if user_id not in USERS:
        USERS[user_id] = {'balance': 0.0, 'referrals': 0, 'referred_by': None, 'active_plans': [], 'referred_users': []}
        
        args = message.text.split()
        if len(args) > 1 and args[1].startswith('ref_'):
            try:
                ref_id = int(args[1].split('_')[1])
                if ref_id in USERS and ref_id != user_id:
                    USERS[user_id]['referred_by'] = ref_id
                    USERS[ref_id]['referrals'] += 1
                    USERS[ref_id]['referred_users'].append(user_id)
                    
                    reward = SETTINGS['refer_reward']
                    USERS[ref_id]['balance'] += reward
                    bot.send_message(ref_id, f"🎉 *Congratulations!* You received **₹{reward}** for referring a new user.", parse_mode='Markdown')
            except:
                pass

    # Check if user has joined all required channels
    if not check_subscription(user_id):
        markup = InlineKeyboardMarkup(row_width=1)
        for ch in CHANNELS:
            markup.add(InlineKeyboardButton(f"📢 Join {ch['name']}", url=ch['url']))
        markup.add(InlineKeyboardButton("🔄 Verify Joined Channels", callback_data='verify_join'))

        welcome_text = (
            "╔════════════════════╗\n"
            "      💎 **PREMIUM VIP STORE** 💎\n"
            "╚════════════════════╝\n\n"
            "⭐ **Rating:** `4.9 / 5.0` (14,250+ Trusted Users)\n"
            "⚠️ *Access blocked! Aapne hamare sabhi official channels join nahi kiye hain.*\n\n"
            "👇 *Pehle neeche diye gaye sabhi channels join karein, phir 'Verify Joined Channels' par click karein:*"
        )
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')
        return

    # If already joined
    bot.send_message(
        message.chat.id,
        "🚀 *Access Granted!* Welcome to the VIP dashboard. Use the keyboard below:",
        reply_markup=main_reply_keyboard(user_id),
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'verify_join')
def verify_join(call):
    user_id = call.from_user.id
    
    if check_subscription(user_id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.send_message(
            call.message.chat.id,
            "🚀 *Verification Successful!* Welcome to the VIP dashboard. Use the keyboard below:",
            reply_markup=main_reply_keyboard(user_id),
            parse_mode='Markdown'
        )
    else:
        bot.answer_callback_query(call.id, "❌ Aapne abhi tak sabhi channels join nahi kiye hain! Pehle join karein.", show_alert=True)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    
    # Enforce channel join check on any message if not joined
    if not check_subscription(user_id):
        markup = InlineKeyboardMarkup(row_width=1)
        for ch in CHANNELS:
            markup.add(InlineKeyboardButton(f"📢 Join {ch['name']}", url=ch['url']))
        markup.add(InlineKeyboardButton("🔄 Verify Joined Channels", callback_data='verify_join'))
        bot.send_message(message.chat.id, "⚠️ *Aapko bot use karne ke liye pehle hamare sabhi channels join karne honge!*", reply_markup=markup, parse_mode='Markdown')
        return

    text = message.text
    username = message.from_user.username or str(message.from_user.first_name)

    menu_buttons = ["🛒 CC Store", "❤️ Like Store", "👛 My Wallet", "➕ Add Money", "👥 Refer & Earn", "🛠️ Support", "📦 My Active Plans", "👑 Admin Panel"]
    if text in menu_buttons:
        if user_id in USER_STATE:
            USER_STATE[user_id] = None

    if user_id == ADMIN_ID:
        state = ADMIN_STATE.get('action')
        
        if state == 'add_bal_get_id':
            try:
                target_user_id = int(text.strip())
                if target_user_id not in USERS:
                    USERS[target_user_id] = {'balance': 0.0, 'referrals': 0, 'referred_by': None, 'active_plans': [], 'referred_users': []}
                ADMIN_STATE['target_user'] = target_user_id
                ADMIN_STATE['action'] = 'add_bal_get_amount'
                bot.send_message(message.chat.id, f"✅ Target User Found (`{target_user_id}`).\n\n💵 *Ab kitna amount add karna hai?* (e.g. 100, 500):", parse_mode='Markdown')
            except ValueError:
                bot.send_message(message.chat.id, "❌ *Invalid User ID!* Numbers only enter karein.", parse_mode='Markdown')
            return

        elif state == 'add_bal_get_amount':
            try:
                amount = float(text.strip())
                target_user_id = ADMIN_STATE['target_user']
                USERS[target_user_id]['balance'] += amount
                ADMIN_STATE.clear()
                bot.send_message(message.chat.id, f"✅ Successfully added **₹{amount}** to User ID: `{target_user_id}`!", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
                bot.send_message(target_user_id, f"🎉 *Good News!* Admin has added **₹{amount}** to your wallet.", parse_mode='Markdown')
            except ValueError:
                bot.send_message(message.chat.id, "❌ *Invalid amount!* Sahi numeric value enter karein.", parse_mode='Markdown')
            return

        elif state == 'check_bal_get_id':
            try:
                target_user_id = int(text.strip())
                ADMIN_STATE.clear()
                balance = USERS.get(target_user_id, {}).get('balance', 0.0)
                refs = USERS.get(target_user_id, {}).get('referrals', 0)
                info_msg = f"👤 **USER PROFILE INFO**\n\n🆔 UID: `{target_user_id}`\n💰 Balance: **₹{balance}**\n👥 Referrals: **{refs}**"
                bot.send_message(message.chat.id, info_msg, parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))
            except ValueError:
                bot.send_message(message.chat.id, "❌ *Invalid User ID!*", parse_mode='Markdown')
            return

        elif state == 'edit_refer_reward':
            try:
                new_reward = float(text.strip())
                SETTINGS['refer_reward'] = new_reward
                ADMIN_STATE.clear()
                bot.send_message(message.chat.id, f"✅ Refer reward successfully updated to **₹{new_reward}** per refer!", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
            except ValueError:
                bot.send_message(message.chat.id, "❌ *Invalid amount!* Sahi number dalein.", parse_mode='Markdown')
            return

        elif state == 'edit_cc_price':
            plan_key = ADMIN_STATE.get('plan_key')
            if plan_key in CC_PLANS:
                CC_PLANS[plan_key]['display_price'] = text.strip()
                cleaned = ''.join([c for c in text if c.isdigit()])
                CC_PLANS[plan_key]['price'] = cleaned if cleaned else "0"
            ADMIN_STATE.clear()
            bot.send_message(message.chat.id, f"✅ CC Plan price successfully updated to *{text}*!", parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))
            return

        elif state == 'edit_cc_details':
            plan_key = ADMIN_STATE.get('plan_key')
            if plan_key in CC_PLANS:
                CC_PLANS[plan_key]['details'] = text.strip()
            ADMIN_STATE.clear()
            bot.send_message(message.chat.id, f"✅ CC Plan details successfully updated!", parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))
            return

        elif state == 'edit_like_price':
            plan_key = ADMIN_STATE.get('plan_key')
            if plan_key in LIKE_PLANS:
                LIKE_PLANS[plan_key]['display_price'] = text.strip()
                cleaned = ''.join([c for c in text if c.isdigit()])
                LIKE_PLANS[plan_key]['price'] = cleaned if cleaned else "0"
            ADMIN_STATE.clear()
            bot.send_message(message.chat.id, f"✅ Like Pack price successfully updated to *{text}*!", parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))
            return

        elif state == 'edit_like_details':
            plan_key = ADMIN_STATE.get('plan_key')
            if plan_key in LIKE_PLANS:
                LIKE_PLANS[plan_key]['details'] = text.strip()
            ADMIN_STATE.clear()
            bot.send_message(message.chat.id, f"✅ Like Pack details successfully updated!", parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))
            return

        elif state == 'add_new_cc_name':
            ADMIN_STATE['new_cc_name'] = text.strip()
            ADMIN_STATE['action'] = 'add_new_cc_price'
            bot.send_message(message.chat.id, "💵 Enter price for new CC plan (e.g. ₹299):", parse_mode='Markdown')
            return

        elif state == 'add_new_cc_price':
            price_text = text.strip()
            cleaned = ''.join([c for c in price_text if c.isdigit()])
            ADMIN_STATE['new_cc_price'] = cleaned if cleaned else "0"
            ADMIN_STATE['new_cc_display'] = price_text
            ADMIN_STATE['action'] = 'add_new_cc_details'
            bot.send_message(message.chat.id, "📝 Enter card details/format for this new CC plan:", parse_mode='Markdown')
            return

        elif state == 'add_new_cc_details':
            details = text.strip()
            name = ADMIN_STATE['new_cc_name']
            price = ADMIN_STATE['new_cc_price']
            display = ADMIN_STATE['new_cc_display']
            
            key = f"custom_cc_{len(CC_PLANS) + 1}"
            CC_PLANS[key] = {
                "name": f"💳 **{name}**",
                "price": price,
                "display_price": display,
                "value": "Custom",
                "details": details
            }
            ADMIN_STATE.clear()
            bot.send_message(message.chat.id, f"✅ New CC Plan successfully added to the store!", parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))
            return

        elif state == 'add_new_like_name':
            ADMIN_STATE['new_like_name'] = text.strip()
            ADMIN_STATE['action'] = 'add_new_like_price'
            bot.send_message(message.chat.id, "💵 Enter price for new Like Pack (e.g. ₹150):", parse_mode='Markdown')
            return

        elif state == 'add_new_like_price':
            price_text = text.strip()
            cleaned = ''.join([c for c in price_text if c.isdigit()])
            ADMIN_STATE['new_like_price'] = cleaned if cleaned else "0"
            ADMIN_STATE['new_like_display'] = price_text
            ADMIN_STATE['action'] = 'add_new_like_details'
            bot.send_message(message.chat.id, "📝 Enter description/details for this Like Pack:", parse_mode='Markdown')
            return

        elif state == 'add_new_like_details':
            details = text.strip()
            name = ADMIN_STATE['new_like_name']
            price = ADMIN_STATE['new_like_price']
            display = ADMIN_STATE['new_like_display']
            
            key = f"custom_like_{len(LIKE_PLANS) + 1}"
            LIKE_PLANS[key] = {
                "name": f"❤️ **{name}**",
                "price": price,
                "display_price": display,
                "days": 30,
                "daily": 220,
                "total": 5000,
                "details": details
            }
            ADMIN_STATE.clear()
            bot.send_message(message.chat.id, f"✅ New Like Pack successfully added to the store!", parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))
            return

    if USER_STATE.get(user_id) == 'waiting_for_amount':
        text_clean = text.strip()
        if not text_clean.isdigit():
            bot.send_message(message.chat.id, "❌ *Error:* Please enter a valid amount in numbers (e.g., 100, 500).", parse_mode='Markdown')
            return
        
        try:
            amount = float(text_clean)
            if amount <= 0:
                raise ValueError()
            USER_STATE[user_id] = {'state': 'waiting_for_utr', 'amount': amount}
            
            pay_text = (
                "💎 **SECURE PAYMENT GATEWAY**\n\n"
                f"💵 Amount to Pay: **₹{amount}**\n"
                "🎯 UPI ID: `sima6241@ptaxis`\n\n"
                "📌 *Instructions:*\n"
                "1. Pay via UPI to `sima6241@ptaxis`.\n"
                "2. Send your 12-digit UTR ID here in the chat."
            )
            bot.send_message(message.chat.id, pay_text, parse_mode='Markdown')
        except ValueError:
            bot.send_message(message.chat.id, "❌ *Please enter a valid amount in numbers.*", parse_mode='Markdown')
        return

    elif isinstance(USER_STATE.get(user_id), dict) and USER_STATE[user_id].get('state') == 'waiting_for_utr':
        utr = text.strip()
        amount = USER_STATE[user_id]['amount']
        USER_STATE[user_id] = None
        
        bot.send_message(message.chat.id, "✅ *Proof Submitted Successfully!*\n\nAdmin will verify your UTR and approve funds shortly.", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{amount}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
        )
        admin_alert = (
            "🔔 **NEW PAYMENT PROOF**\n\n"
            f"👤 User: {username} (ID: `{user_id}`)\n"
            f"💵 Amount: **₹{amount}**\n"
            f"🧾 UTR: `{utr}`"
        )
        bot.send_message(ADMIN_ID, admin_alert, reply_markup=markup, parse_mode='Markdown')
        return

    if text == "🛒 CC Store":
        store_msg = (
            "╔════════════════════╗\n"
            "      💎 **CC STORE** 💎\n"
            "╚════════════════════╝\n\n"
            "⭐ *Rating:* `4.9 / 5.0` | 🚀 *Select a CC Package below:*"
        )
        markup = InlineKeyboardMarkup(row_width=1)
        for key, plan in CC_PLANS.items():
            markup.add(InlineKeyboardButton(f"⚡ {plan['name']} ➔ {plan['display_price']} ({plan['value']})", callback_data=key))
        bot.send_message(message.chat.id, store_msg, reply_markup=markup, parse_mode='Markdown')

    elif text == "❤️ Like Store":
        store_msg = (
            "╔════════════════════╗\n"
            "     ❤️ **LIKE STORE** ❤️\n"
            "╚════════════════════╝\n\n"
            "⭐ *Rating:* `4.9 / 5.0` | 🚀 *Select a Like Package below:*"
        )
        markup = InlineKeyboardMarkup(row_width=1)
        for key, plan in LIKE_PLANS.items():
            markup.add(InlineKeyboardButton(f"⚡ {plan['name']} ➔ {plan['display_price']}", callback_data=key))
        bot.send_message(message.chat.id, store_msg, reply_markup=markup, parse_mode='Markdown')

    elif text == "📦 My Active Plans":
        user_data = USERS.get(user_id, {'active_plans': []})
        active_plans = user_data.get('active_plans', [])
        
        if not active_plans:
            bot.send_message(message.chat.id, "📦 *Aapka koi bhi active plan nahi hai!*", parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))
        else:
            msg = "📦 **YOUR ACTIVE PLANS:**\n\n"
            for p in active_plans:
                msg +=
