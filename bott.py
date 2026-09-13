import os
from flask import Flask
from threading import Thread
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

TOKEN = '8999778583:AAFD-sqVK_HsGDs5v3xIcQum8_tLnJeU6AE'
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
        "details": "```\n|           P R I M E   V I S A         |\n|___________|\n|                                       |\n|  HOLDER : horiyo soli                 |\n|  STATE  : Delhi                       |\n|                                       |\n|  CARD   : 4100 2800 0000 1007         |\n|  VALID  : 06 / 30                     |\n|  CVV    : 635                         |\n|___________|\n```"
    },
    'plan_199': {
        "name": "💳 **PLAN 2**", 
        "price": "199", 
        "display_price": "₹199", 
        "value": "6.5K Value",
        "details": "```\n╔═══════════ PRIME CARD 2 ════════════════╗\n║                                       ║\n║  HOLDER : MITOY DOWL                  ║\n║  STATE  : Delhi                       ║\n║                                       ║\n║  CARD   : 8176 0631 5600 4748         ║\n║  VALID  : 07 / 32                     ║\n║  CVV    : 917                         ║\n║                                       ║\n╚═══════════════════════════════════════╝\n```"
    },
    'plan_599': {
        "name": "💳 **PLAN 3**", 
        "price": "599", 
        "display_price": "₹599", 
        "value": "26K Value",
        "details": "```\n|           P R I M E   V I S A         |\n|___________|\n|                                       |\n|  HOLDER : horiyo soli                 |\n|  STATE  : Delhi                       |\n|                                       |\n|  CARD   : 4100 2800 0000 1007         |\n|  VALID  : 06 / 30                     |\n|  CVV    : 635                         |\n|___________|\n```"
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

def get_user(user_id):
    if user_id not in USERS:
        USERS[user_id] = {
            'balance': 0.0,
            'referrals': 0,
            'referred_by': None,
            'active_plans': [],
            'referred_users': []
        }
    return USERS[user_id]

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
    if user_id == ADMIN_ID:
        return True
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch['username'], user_id)
            if member.status not in ['creator', 'administrator', 'member']:
                return False
        except Exception:
            return False
    return True

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('ref_'):
        try:
            ref_id = int(args[1].split('_')[1])
            if ref_id != user_id and user_data['referred_by'] is None:
                ref_data = get_user(ref_id)
                user_data['referred_by'] = ref_id
                ref_data['referrals'] += 1
                if user_id not in ref_data['referred_users']:
                    ref_data['referred_users'].append(user_id)
                
                reward = SETTINGS['refer_reward']
                ref_data['balance'] += reward
                bot.send_message(ref_id, f"🎉 *Congratulations!* You received **₹{reward}** for referring User `{user_id}`.", parse_mode='Markdown')
        except Exception as e:
            print(f"Ref Error: {e}")

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
    text = message.text.strip()
    username = message.from_user.username or str(message.from_user.first_name)
    user_data = get_user(user_id)

    if not check_subscription(user_id):
        markup = InlineKeyboardMarkup(row_width=1)
        for ch in CHANNELS:
            markup.add(InlineKeyboardButton(f"📢 Join {ch['name']}", url=ch['url']))
        markup.add(InlineKeyboardButton("🔄 Verify Joined Channels", callback_data='verify_join'))
        bot.send_message(message.chat.id, "⚠️ *Aapko bot use karne ke liye pehle hamare sabhi channels join karne honge!*", reply_markup=markup, parse_mode='Markdown')
        return

    if user_id == ADMIN_ID and user_id in ADMIN_STATE:
        state = ADMIN_STATE[user_id].get('action')
        
        if state == 'add_bal_get_id':
            try:
                target_user_id = int(text)
                ADMIN_STATE[user_id]['target_user'] = target_user_id
                ADMIN_STATE[user_id]['action'] = 'add_bal_get_amount'
                bot.send_message(message.chat.id, f"✅ Target User Found (`{target_user_id}`).\n\n💵 *Ab kitna amount add karna hai?*:", parse_mode='Markdown')
            except ValueError:
                bot.send_message(message.chat.id, "❌ *Invalid User ID!* Numbers only enter karein.", parse_mode='Markdown')
            return

        elif state == 'add_bal_get_amount':
            try:
                amount = float(text)
                target_user_id = ADMIN_STATE[user_id]['target_user']
                target_data = get_user(target_user_id)
                target_data['balance'] += amount
                ADMIN_STATE.pop(user_id, None)
                bot.send_message(message.chat.id, f"✅ Successfully added **₹{amount}** to User ID: `{target_user_id}`!", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
                bot.send_message(target_user_id, f"🎉 *Good News!* Admin has added **₹{amount}** to your wallet.", parse_mode='Markdown')
            except ValueError:
                bot.send_message(message.chat.id, "❌ *Invalid amount!* Sahi numeric value enter karein.", parse_mode='Markdown')
            return

        elif state == 'edit_cc_price':
            plan_key = ADMIN_STATE[user_id].get('plan_key')
            if plan_key in CC_PLANS:
                CC_PLANS[plan_key]['display_price'] = text
                cleaned = ''.join([c for c in text if c.isdigit()])
                CC_PLANS[plan_key]['price'] = cleaned if cleaned else "0"
            ADMIN_STATE.pop(user_id, None)
            bot.send_message(message.chat.id, f"✅ CC Plan price successfully updated to *{text}*!", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
            return

        elif state == 'edit_cc_details':
            plan_key = ADMIN_STATE[user_id].get('plan_key')
            if plan_key in CC_PLANS:
                CC_PLANS[plan_key]['details'] = text
            ADMIN_STATE.pop(user_id, None)
            bot.send_message(message.chat.id, f"✅ CC Plan details successfully updated!", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
            return

        elif state == 'edit_like_price':
            plan_key = ADMIN_STATE[user_id].get('plan_key')
            if plan_key in LIKE_PLANS:
                LIKE_PLANS[plan_key]['display_price'] = text
                cleaned = ''.join([c for c in text if c.isdigit()])
                LIKE_PLANS[plan_key]['price'] = cleaned if cleaned else "0"
            ADMIN_STATE.pop(user_id, None)
            bot.send_message(message.chat.id, f"✅ Like Pack price successfully updated to *{text}*!", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
            return

        elif state == 'edit_like_details':
            plan_key = ADMIN_STATE[user_id].get('plan_key')
            if plan_key in LIKE_PLANS:
                LIKE_PLANS[plan_key]['details'] = text
            ADMIN_STATE.pop(user_id, None)
            bot.send_message(message.chat.id, f"✅ Like Pack details successfully updated!", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
            return

    if user_id in USER_STATE and USER_STATE[user_id].get('state') == 'waiting_for_amount':
        if not text.isdigit():
            bot.send_message(message.chat.id, "❌ *Error:* Please enter a valid amount in numbers (e.g., 100, 500).", parse_mode='Markdown')
            return
        
        try:
            amount = float(text)
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

    elif user_id in USER_STATE and USER_STATE[user_id].get('state') == 'waiting_for_utr':
        utr = text
        amount = USER_STATE[user_id]['amount']
        USER_STATE.pop(user_id, None)
        
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
        active_plans = user_data.get('active_plans', [])
        if not active_plans:
            bot.send_message(message.chat.id, "📦 *Aapka koi bhi active plan nahi hai!*", parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))
        else:
            msg = "📦 **YOUR ACTIVE PLANS:**\n\n"
            for p in active_plans:
                msg += f"🔹 **{p['name']}**\n📅 Expires On: `{p['expiry']}`\n\n"
            bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))

    elif text == "👛 My Wallet":
        wallet_text = (
            "╔════════════════════╗\n"
            "     👛 **VIP WALLET**\n"
            "╚════════════════════╝\n\n"
            f"🆔 UID: `{user_id}`\n"
            f"💰 Balance: **₹{user_data['balance']}**\n"
            f"👥 Total Referrals: **{user_data['referrals']} Users**"
        )
        bot.send_message(message.chat.id, wallet_text, parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))

    elif text == "➕ Add Money":
        USER_STATE[user_id] = {'state': 'waiting_for_amount'}
        bot.send_message(message.chat.id, "➕ **ADD MONEY**\n\n💵 *Kitna amount add karna hai? (Sirf numbers mein likhein, jaise: 100):*", parse_mode='Markdown')

    elif text == "👥 Refer & Earn":
        bot_uname = bot.get_me().username
        ref_link = f"https://t.me/{bot_uname}?start=ref_{user_id}"
        reward = SETTINGS['refer_reward']
        
        ref_list_str = ""
        if user_data['referred_users']:
            ref_list_str = "\n📌 *Aapke referred users (UIDs):*\n" + "\n".join([f"• `{uid}`" for uid in user_data['referred_users']])
        else:
            ref_list_str = "\n📌 *Aapne abhi tak kisi ko refer nahi kiya hai.*"

        ref_text = (
            "🎁 **REFER & EARN PROGRAM**\n\n"
            f"1️⃣ Instant Joining Bonus: **₹{reward}** per refer!\n"
            f"2️⃣ Commission Bonus: **20%** jab aapka referred user koi bhi plan buy karega!\n\n"
            f"👥 Total Referrals: **{user_data['referrals']} Users**\n"
            f"{ref_list_str}\n\n"
            "🔗 *Your Invite Link:*\n"
            f"`{ref_link}`"
        )
        bot.send_message(message.chat.id, ref_text, parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))

    elif text == "🛠️ Support":
        support_text = (
            "🛠️ **VIP SUPPORT**\n\n"
            "💬 Contact Admin: `@Xenon_ask9`\n"
            "🌐 Website: [Click Here to Visit Website](https://web-cc-4.onrender.com/products)"
        )
        bot.send_message(message.chat.id, support_text, parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))

    elif text == "👑 Admin Panel" and user_id == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("➕ Add Balance to User", callback_data='admin_add_money'),
            InlineKeyboardButton("⚙️ Edit CC/Like Prices & Details", callback_data='admin_edit_prices'),
            InlineKeyboardButton("📊 Stats & Users", callback_data='admin_stats')
        )
        bot.send_message(message.chat.id, "👑 **VIP ADMIN CONTROL PANEL**\n\nSelect an operation:", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_') or call.data.startswith('edit_'))
def handle_admin_panels(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        return

    if call.data == 'admin_add_money':
        if user_id not in ADMIN_STATE:
            ADMIN_STATE[user_id] = {}
        ADMIN_STATE[user_id]['action'] = 'add_bal_get_id'
        bot.send_message(call.message.chat.id, "📥 *Enter the Target User ID*:", parse_mode='Markdown')

    elif call.data == 'admin_edit_prices':
        markup = InlineKeyboardMarkup(row_width=1)
        for key, plan in CC_PLANS.items():
            markup.add(
                InlineKeyboardButton(f"💵 CC: {plan['name']} (Price)", callback_data=f"editccprice_{key}"),
                InlineKeyboardButton(f"📝 CC: {plan['name']} (Details)", callback_data=f"editccdetails_{key}")
            )
        for key, plan in LIKE_PLANS.items():
            markup.add(
                InlineKeyboardButton(f"💵 Like: {plan['name']} (Price)", callback_data=f"editlikeprice_{key}"),
                InlineKeyboardButton(f"📝 Like: {plan['name']} (Details)", callback_data=f"editlikedetails_{key}")
            )
        bot.send_message(call.message.chat.id, "⚙️ *Select what you want to edit:*", reply_markup=markup, parse_mode='Markdown')

    elif call.data == 'admin_stats':
        total_balance = sum([u['balance'] for u in USERS.values()])
        bot.send_message(call.message.chat.id, f"📊 **Bot Statistics:**\n\n👥 Total Users: {len(USERS)}\n💰 Total User Balances: ₹{total_balance}\n📦 Total Purchases: {len(PURCHASE_HISTORY)}", parse_mode='Markdown')

    elif call.data.startswith('editccprice_'):
        plan_key = call.data.split('_')[1]
        if user_id not in ADMIN_STATE:
            ADMIN_STATE[user_id] = {}
        ADMIN_STATE[user_id]['action'] = 'edit_cc_price'
        ADMIN_STATE[user_id]['plan_key'] = plan_key
        bot.send_message(call.message.chat.id, "💵 Enter new price display for CC Plan (e.g. ₹149):", parse_mode='Markdown')

    elif call.data.startswith('editccdetails_'):
      plan_key = call.data.split('_')[1]
        if user_id not in ADMIN_STATE:
            ADMIN_STATE[user_id] = {}
        ADMIN_STATE[user_id]['action'] = 'edit_cc_details'
        ADMIN_STATE[user_id]['plan_key'] = plan_key
        bot.send_message(call.message.chat.id, "📝 Enter new details format for CC Plan:", parse_mode='Markdown')

    elif call.data.startswith('editlikeprice_'):
        plan_key = call.data.split('_')[1]
        if user_id not in ADMIN_STATE:
            ADMIN_STATE[user_id] = {}
        ADMIN_STATE[user_id]['action'] = 'edit_like_price'
        ADMIN_STATE[user_id]['plan_key'] = plan_key
        bot.send_message(call.message.chat.id, "💵 Enter new price display for Like Pack (e.g. ₹99):", parse_mode='Markdown')

    elif call.data.startswith('editlikedetails_'):
        plan_key = call.data.split('_')[1]
        if user_id not in ADMIN_STATE:
            ADMIN_STATE[user_id] = {}
        ADMIN_STATE[user_id]['action'] = 'edit_like_details'
        ADMIN_STATE[user_id]['plan_key'] = plan_key
        bot.send_message(call.message.chat.id, "📝 Enter new description for Like Pack:", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_') or call.data.startswith('reject_'))
def handle_payment_approval(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    data = call.data.split('_')
    action = data[0]
    target_user_id = int(data[1])
    
    if action == 'approve':
        amount = float(data[2])
        target_data = get_user(target_user_id)
        target_data['balance'] += amount
        try:
            bot.edit_message_text(f"✅ *Approved & Credited ₹{amount}* to User `{target_user_id}`", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        except:
            pass
        bot.send_message(target_user_id, f"🎉 *Payment Approved!* **₹{amount}** has been added to your wallet.", parse_mode='Markdown')
    elif action == 'reject':
        try:
            bot.edit_message_text(f"❌ *Payment Rejected* for User `{target_user_id}`", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        except:
            pass
        bot.send_message(target_user_id, "❌ *Payment Rejected!* Please contact support or check your UTR.", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data in CC_PLANS.keys())
def handle_cc_purchase(call):
    user_id = call.from_user.id
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ Pehle sabhi channels join karein!", show_alert=True)
        return

    plan_key = call.data
    plan = CC_PLANS.get(plan_key)
    user_data = get_user(user_id)
    user_balance = user_data.get('balance', 0.0)
    
    try:
        price_val = float(plan['price'])
    except:
        price_val = 0.0
    
    markup = InlineKeyboardMarkup()
    if user_balance >= price_val and price_val > 0:
        markup.add(InlineKeyboardButton("✅ Confirm & Purchase Now", callback_data=f'confirmcc_{plan_key}'))
    elif price_val == 0:
        markup.add(InlineKeyboardButton("💬 Contact Admin for Custom Pack", url="https://t.me/Xenon_ask9"))
    else:
        markup.add(InlineKeyboardButton("❌ Insufficient Balance (Add Money)", callback_data='go_add_money'))
        
    preview_msg = (
        "╔════════════════════╗\n"
        f"      📦 **{plan['name']}** 📦\n"
        "╚════════════════════╝\n\n"
        "⭐ **Rating:** `4.9 / 5.0` (Trusted Pack)\n"
        f"💎 Value: **{plan['value']}**\n"
        f"💰 Price: **{plan['display_price']}**\n"
        f"👛 Your Wallet: **₹{user_balance}**\n\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(call.message.chat.id, preview_msg, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirmcc_'))
def confirm_cc_purchase(call):
    user_id = call.from_user.id
    plan_key = call.data.replace('confirmcc_', '')
    plan = CC_PLANS.get(plan_key)
    
    price_val = float(plan['price'])
    user_data = get_user(user_id)
    
    if user_data['balance'] < price_val:
        bot.answer_callback_query(call.id, "❌ Error: Insufficient balance in wallet!", show_alert=True)
        return
    
    user_data['balance'] -= price_val
    
    referred_by = user_data.get('referred_by')
    if referred_by:
        ref_data = get_user(referred_by)
        commission = price_val * 0.20
        ref_data['balance'] += commission
        bot.send_message(referred_by, f"🎁 *Commission Earned!* Aapke referred user ne plan buy kiya aur aapko **₹{commission}** (20%) commission mila hai!", parse_mode='Markdown')

    PURCHASE_HISTORY.append({'user_id': user_id, 'plan': plan['name'], 'price': plan['display_price']})
    
    success_msg = (
        "╔════════════════════╗\n"
        "   📦 **PURCHASE SUCCESSFUL** 📦\n"
        "╚════════════════════╝\n\n"
        f"📦 Plan: {plan['name']}\n"
        f"💎 Value: {plan['value']}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"Here is your CC Data:\n{plan['details']}\n\n"
        "⚠️ *Save this data securely!*"
    )
    bot.send_message(call.message.chat.id, success_msg, parse_mode='Markdown')
    bot.send_message(ADMIN_ID, f"🔔 *New CC Store Order!*\nUser ID: `{user_id}` bought: {plan['name']} ({plan['display_price']})", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data in LIKE_PLANS.keys())
def handle_like_purchase(call):
    user_id = call.from_user.id
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ Pehle sabhi channels join karein!", show_alert=True)
        return

    plan_key = call.data
    plan = LIKE_PLANS.get(plan_key)
    user_data = get_user(user_id)
    user_balance = user_data.get('balance', 0.0)
    
    try:
        price_val = float(plan['price'])
    except:
        price_val = 0.0
    
    markup = InlineKeyboardMarkup()
    if user_balance >= price_val:
        markup.add(InlineKeyboardButton("✅ Confirm & Purchase Now", callback_data=f'confirmlike_{plan_key}'))
    else:
        markup.add(InlineKeyboardButton("❌ Insufficient Balance (Add Money)", callback_data='go_add_money'))
        
    preview_msg = (
        "╔════════════════════╗\n"
        f"      📦 **{plan['name']}** 📦\n"
        "╚════════════════════╝\n\n"
        "⭐ **Rating:** `5.0 / 5.0` (Verified Instant Delivery)\n"
        f"{plan['details']}\n\n"
        f"💰 Price: **{plan['display_price']}**\n"
        f"👛 Your Wallet: **₹{user_balance}**\n\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(call.message.chat.id, preview_msg, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirmlike_'))
def confirm_like_purchase(call):
    user_id = call.from_user.id
    plan_key = call.data.replace('confirmlike_', '')
    plan = LIKE_PLANS.get(plan_key)
    
    price_val = float(plan['price'])
    user_data = get_user(user_id)
    
    if user_data['balance'] < price_val:
        bot.answer_callback_query(call.id, "❌ Error: Insufficient balance in wallet!", show_alert=True)
        return
    
    user_data['balance'] -= price_val

    referred_by = user_data.get('referred_by')
    if referred_by:
        ref_data = get_user(referred_by)
        commission = price_val * 0.20
        ref_data['balance'] += commission
        bot.send_message(referred_by, f"🎁 *Commission Earned!* Aapke referred user ne Like Pack buy kiya aur aapko **₹{commission}** (20%) commission mila hai!", parse_mode='Markdown')

    expiry_date = (datetime.now() + timedelta(days=plan['days'])).strftime("%d-%m-%Y %H:%M")
    
    user_data['active_plans'].append({
        'name': f"{plan['name']} ({plan['total']} Likes)",
        'expiry': expiry_date
    })
    
    PURCHASE_HISTORY.append({'user_id': user_id, 'plan': plan['name'], 'price': plan['display_price']})
    
    success_msg = (
        "╔════════════════════╗\n"
        "   🎉 **ORDER SUCCESSFUL** 🎉\n"
        "╚════════════════════╝\n\n"
        f"📦 Plan: {plan['name']}\n"
        f"❤️ Total Likes: {plan['total']} ({plan['daily']} Daily)\n"
        f"📅 Valid Till: `{expiry_date}`\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🛡️ *Your active plan has been saved! Check 'My Active Plans'.*"
    )
    bot.send_message(call.message.chat.id, success_msg, parse_mode='Markdown')
    bot.send_message(ADMIN_ID, f"🔔 *New Like Store Order!*\nUser ID: `{user_id}` bought: {plan['name']} ({plan['display_price']})", parse_mode='Markdown')

if __name__ == '__main__':
    print("💎 CC & Like Store Bot is running successfully...")
    keep_alive()
    bot.infinity_polling()
