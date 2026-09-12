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
    {"name": "Proof Channel", "url": "https://t.me/botlikeproof"},
    {"name": "Earning Channel 1", "url": "https://t.me/eraningwithask"},
    {"name": "Earning Channel 2", "url": "https://t.me/eraningwithask9"}
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
        "name": "PLAN 1", 
        "price": "100", 
        "display_price": "₹100", 
        "value": "3K Value",
        "details": "CC Data: 411122XXXXXXXXXX | 12/28 | 123 | 3K Balance Data"
    },
    'plan_199': {
        "name": "PLAN 2", 
        "price": "199", 
        "display_price": "₹199", 
        "value": "6.5K Value",
        "details": "CC Data: 555544XXXXXXXXXX | 10/26 | 456 | 6.5K Balance Data"
    },
    'plan_599': {
        "name": "PLAN 3", 
        "price": "599", 
        "display_price": "₹599", 
        "value": "26K Value",
        "details": "CC Data: 378282XXXXXXXXXX | 05/27 | 789 | 26K Balance Data"
    },
    'plan_custom': {
        "name": "CUSTOM PLAN", 
        "price": "0", 
        "display_price": "Special", 
        "value": "Custom",
        "details": "Special CC Pack: Contact Admin directly."
    }
}

LIKE_PLANS = {
    'like_60': {
        "name": "LIKE PACK 1",
        "price": "60",
        "display_price": "₹60",
        "days": 15,
        "daily": 220,
        "total": 3300,
        "details": "220 Likes Daily\nDuration: 15 Days\nTotal: 3,300 Likes"
    },
    'like_120': {
        "name": "LIKE PACK 2",
        "price": "120",
        "display_price": "₹120",
        "days": 30,
        "daily": 220,
        "total": 6600,
        "details": "220 Likes Daily\nDuration: 30 Days\nTotal: 6,600 Likes"
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
                    bot.send_message(ref_id, f"🎉 Congratulations! You received ₹{reward} for referring a new user.")
            except:
                pass

    markup = InlineKeyboardMarkup(row_width=1)
    for ch in CHANNELS:
        markup.add(InlineKeyboardButton(f"📢 Join {ch['name']}", url=ch['url']))
    markup.add(InlineKeyboardButton("✨ Verify & Launch Bot ✨", callback_data='verify_join'))

    welcome_text = (
        "╔════════════════════╗\n"
        "      💎 PREMIUM STORE 💎\n"
        "╚════════════════════╝\n\n"
        "🚀 Fast, Secure & Automated CC & Like Store!\n\n"
        "⚠️ To access the bot, please join our official channels below:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'verify_join')
def verify_join(call):
    user_id = call.from_user.id
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    bot.send_message(
        call.message.chat.id,
        "🚀 Access Granted! Welcome to the VIP dashboard. Use the keyboard below:",
        reply_markup=main_reply_keyboard(user_id)
    )

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
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
                bot.send_message(message.chat.id, f"✅ Target User Found ({target_user_id}).\n\n💵 Ab kitna amount add karna hai? (e.g. 100, 500):")
            except ValueError:
                bot.send_message(message.chat.id, "❌ Invalid User ID! Numbers only enter karein.")
            return

        elif state == 'add_bal_get_amount':
            try:
                amount = float(text.strip())
                target_user_id = ADMIN_STATE['target_user']
                USERS[target_user_id]['balance'] += amount
                ADMIN_STATE.clear()
                bot.send_message(message.chat.id, f"✅ Successfully added ₹{amount} to User ID: {target_user_id}!", reply_markup=main_reply_keyboard(user_id))
                bot.send_message(target_user_id, f"🎉 Good News! Admin has added ₹{amount} to your wallet.")
            except ValueError:
                bot.send_message(message.chat.id, "❌ Invalid amount! Sahi numeric value enter karein.")
            return

        elif state == 'check_bal_get_id':
            try:
                target_user_id = int(text.strip())
                ADMIN_STATE.clear()
                balance = USERS.get(target_user_id, {}).get('balance', 0.0)
                refs = USERS.get(target_user_id, {}).get('referrals', 0)
                info_msg = f"👤 USER PROFILE INFO\n\n🆔 UID: {target_user_id}\n💰 Balance: ₹{balance}\n👥 Referrals: {refs}"
                bot.send_message(message.chat.id, info_msg, reply_markup=main_reply_keyboard(user_id))
            except ValueError:
                bot.send_message(message.chat.id, "❌ Invalid User ID!")
            return

        elif state == 'edit_refer_reward':
            try:
                new_reward = float(text.strip())
                SETTINGS['refer_reward'] = new_reward
                ADMIN_STATE.clear()
                bot.send_message(message.chat.id, f"✅ Refer reward successfully updated to ₹{new_reward} per refer!", reply_markup=main_reply_keyboard(user_id))
            except ValueError:
                bot.send_message(message.chat.id, "❌ Invalid amount! Sahi number dalein.")
            return

        elif state == 'edit_cc_price':
            plan_key = ADMIN_STATE['plan_key']
            CC_PLANS[plan_key]['display_price'] = text.strip()
            cleaned = ''.join([c for c in text if c.isdigit()])
            CC_PLANS[plan_key]['price'] = cleaned if cleaned else "0"
            ADMIN_STATE.clear()
            bot.send_message(message.chat.id, f"✅ CC Plan price successfully updated to {text}!", reply_markup=main_reply_keyboard(user_id))
            return

        elif state == 'edit_like_price':
            plan_key = ADMIN_STATE['plan_key']
            LIKE_PLANS[plan_key]['display_price'] = text.strip()
            cleaned = ''.join([c for c in text if c.isdigit()])
            LIKE_PLANS[plan_key]['price'] = cleaned if cleaned else "0"
            ADMIN_STATE.clear()
            bot.send_message(message.chat.id, f"✅ Like Pack price successfully updated to {text}!", reply_markup=main_reply_keyboard(user_id))
            return

    if USER_STATE.get(user_id) == 'waiting_for_amount':
        text_clean = text.strip()
        if not text_clean.isdigit():
            bot.send_message(message.chat.id, "❌ Error: Please enter a valid amount in numbers (e.g., 100, 500).")
            return
        
        try:
            amount = float(text_clean)
            if amount <= 0:
                raise ValueError()
            USER_STATE[user_id] = {'state': 'waiting_for_utr', 'amount': amount}
            
            pay_text = (
                "💎 SECURE PAYMENT GATEWAY\n\n"
                f"💵 Amount to Pay: ₹{amount}\n"
                "🎯 UPI ID: sima6241@ptaxis\n\n"
                "📌 Instructions:\n"
                "1. Pay via UPI to sima6241@ptaxis.\n"
                "2. Send your 12-digit UTR ID here in the chat."
            )
            bot.send_message(message.chat.id, pay_text)
        except ValueError:
            bot.send_message(message.chat.id, "❌ Please enter a valid amount in numbers.")
        return

    elif isinstance(USER_STATE.get(user_id), dict) and USER_STATE[user_id].get('state') == 'waiting_for_utr':
        utr = text.strip()
        amount = USER_STATE[user_id]['amount']
        USER_STATE[user_id] = None
        
        bot.send_message(message.chat.id, "✅ Proof Submitted Successfully!\n\nAdmin will verify your UTR and approve funds shortly.", reply_markup=main_reply_keyboard(user_id))
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{amount}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
        )
        admin_alert = (
            "🔔 NEW PAYMENT PROOF\n\n"
            f"👤 User: {username} (ID: {user_id})\n"
            f"💵 Amount: ₹{amount}\n"
            f"🧾 UTR: {utr}"
        )
        # Safe message send to admin without markdown crashing
        bot.send_message(ADMIN_ID, admin_alert, reply_markup=markup)
        return

    if text == "🛒 CC Store":
        store_msg = (
            "╔════════════════════╗\n"
            "      💎 CC STORE 💎\n"
            "╚════════════════════╝\n\n"
            "🚀 Select a CC Package below:"
        )
        markup = InlineKeyboardMarkup(row_width=1)
        for key, plan in CC_PLANS.items():
            markup.add(InlineKeyboardButton(f"⚡ {plan['name']} ➔ {plan['display_price']} ({plan['value']})", callback_data=key))
        bot.send_message(message.chat.id, store_msg, reply_markup=markup)

    elif text == "❤️ Like Store":
        store_msg = (
            "╔════════════════════╗\n"
            "     ❤️ LIKE STORE ❤️\n"
            "╚════════════════════╝\n\n"
            "🚀 Select a Like Package below:"
        )
        markup = InlineKeyboardMarkup(row_width=1)
        for key, plan in LIKE_PLANS.items():
            markup.add(InlineKeyboardButton(f"⚡ {plan['name']} ➔ {plan['display_price']}", callback_data=key))
        bot.send_message(message.chat.id, store_msg, reply_markup=markup)

    elif text == "📦 My Active Plans":
        user_data = USERS.get(user_id, {'active_plans': []})
        active_plans = user_data.get('active_plans', [])
        
        if not active_plans:
            bot.send_message(message.chat.id, "📦 Aapka koi bhi active plan nahi hai!", reply_markup=main_reply_keyboard(user_id))
        else:
            msg = "📦 YOUR ACTIVE PLANS:\n\n"
            for p in active_plans:
                msg += f"🔹 {p['name']}\n📅 Expires On: {p['expiry']}\n\n"
            bot.send_message(message.chat.id, msg, reply_markup=main_reply_keyboard(user_id))

    elif text == "👛 My Wallet":
        data = USERS.get(user_id, {'balance': 0.0, 'referrals': 0})
        wallet_text = (
            "╔════════════════════╗\n"
            "     👛 VIP WALLET\n"
            "╚════════════════════╝\n\n"
            f"🆔 UID: {user_id}\n"
            f"💰 Balance: ₹{data['balance']}\n"
            f"👥 Total Referrals: {data['referrals']} Users"
        )
        bot.send_message(message.chat.id, wallet_text, reply_markup=main_reply_keyboard(user_id))

    elif text == "➕ Add Money":
        USER_STATE[user_id] = 'waiting_for_amount'
        bot.send_message(message.chat.id, "➕ ADD MONEY\n\n💵 Kitna amount add karna hai? (Sirf numbers mein likhein, jaise: 100):")

    elif text == "👥 Refer & Earn":
        bot_uname = bot.get_me().username
        ref_link = f"https://t.me/{bot_uname}?start=ref_{user_id}"
        reward = SETTINGS['refer_reward']
        user_data = USERS.get(user_id, {'referrals': 0, 'referred_users': []})
        
        ref_list_str = ""
        if user_data['referred_users']:
            ref_list_str = "\n📌 Aapke referred users (UIDs):\n" + "\n".join([f"• {uid}" for uid in user_data['referred_users']])
        else:
            ref_list_str = "\n📌 Aapne abhi tak kisi ko refer nahi kiya hai."

        ref_text = (
            "🎁 REFER & EARN PROGRAM\n\n"
            f"1️⃣ Instant Joining Bonus: ₹{reward} per refer!\n"
            f"2️⃣ Commission Bonus: 20% jab aapka referred user koi bhi plan buy karega!\n\n"
            f"👥 Total Referrals: {user_data['referrals']} Users\n"
            f"{ref_list_str}\n\n"
            "🔗 Your Invite Link:\n"
            f"{ref_link}"
        )
        bot.send_message(message.chat.id, ref_text, reply_markup=main_reply_keyboard(user_id))

    elif text == "🛠️ Support":
        bot.send_message(message.chat.id, "🛠️ VIP SUPPORT\n\n💬 Contact Admin directly: @YourAdminUsername", reply_markup=main_reply_keyboard(user_id))

    elif text == "👑 Admin Panel" and user_id == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("➕ Add Balance to User", callback_data='admin_add_money'),
            InlineKeyboardButton("🔍 Check User Balance", callback_data='admin_check_bal'),
            InlineKeyboardButton("⚙️ Edit CC/Like Prices", callback_data='admin_edit_prices'),
            InlineKeyboardButton("🎁 Set Refer Reward", callback_data='admin_edit_refer'),
            InlineKeyboardButton("📊 Stats & Users", callback_data='admin_stats')
        )
        bot.send_message(message.chat.id, "👑 VIP ADMIN CONTROL PANEL\n\nSelect an operation:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_panels(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        return

    if call.data == 'admin_add_money':
        ADMIN_STATE['action'] = 'add_bal_get_id'
        bot.send_message(call.message.chat.id, "📥 Enter the Target User ID where you want to add balance:")

    elif call.data == 'admin_check_bal':
        ADMIN_STATE['action'] = 'check_bal_get_id'
        bot.send_message(call.message.chat.id, "🔍 Enter the User ID to check balance:")

    elif call.data == 'admin_edit_prices':
        markup = InlineKeyboardMarkup(row_width=1)
        for key, plan in CC_PLANS.items():
            markup.add(InlineKeyboardButton(f"✏️ CC: {plan['name']} ({plan['display_price']})", callback_data=f"editcc_{key}"))
        for key, plan in LIKE_PLANS.items():
            markup.add(InlineKeyboardButton(f"✏️ Like: {plan['name']} ({plan['display_price']})", callback_data=f"editlike_{key}"))
        bot.send_message(call.message.chat.id, "⚙️ Select a Plan to Edit Price:", reply_markup=markup)

    elif call.data == 'admin_edit_refer':
        ADMIN_STATE['action'] = 'edit_refer_reward'
        bot.send_message(call.message.chat.id, f"🎁 Current Refer Reward: ₹{SETTINGS['refer_reward']}\n\nNaya reward amount enter karein (e.g. 10):")

    elif call.data == 'admin_stats':
        bot.send_message(call.message.chat.id, f"📊 Bot Statistics:\n\n👥 Total Users: {len(USERS)}\n📦 Total Purchases: {len(PURCHASE_HISTORY)}\n🎁 Current Refer Bonus: ₹{SETTINGS['refer_reward']}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('editcc_') or call.data.startswith('editlike_'))
def handle_price_edit_menu(call):
    if call.from_user.id != ADMIN_ID:
        return
    data = call.data.split('_')
    action = data[0]
    plan_key = data[1]
    
    if action == 'editcc':
        ADMIN_STATE['action'] = 'edit_cc_price'
        ADMIN_STATE['plan_key'] = plan_key
        bot.send_message(call.message.chat.id, f"💵 Enter new price for {CC_PLANS[plan_key]['name']} (e.g. ₹149):")
    elif action == 'editlike':
        ADMIN_STATE['action'] = 'edit_like_price'
        ADMIN_STATE['plan_key'] = plan_key
        bot.send_message(call.message.chat.id, f"💵 Enter new price for {LIKE_PLANS[plan_key]['name']} (e.g. ₹99):")

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_') or call.data.startswith('reject_'))
def handle_payment_approval(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    data = call.data.split('_')
    action = data[0]
    target_user_id = int(data[1])
    
    if action == 'approve':
        amount = float(data[2])
        if target_user_id not in USERS:
            USERS[target_user_id] = {'balance': 0.0, 'referrals': 0, 'referred_by': None, 'active_plans': [], 'referred_users': []}
        USERS[target_user_id]['balance'] += amount
        try:
            bot.edit_message_text(f"✅ Approved & Credited ₹{amount} to User {target_user_id}", call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.send_message(target_user_id, f"🎉 Payment Approved! ₹{amount} has been added to your wallet.")
    elif action == 'reject':
        try:
            bot.edit_message_text(f"❌ Payment Rejected for User {target_user_id}", call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.send_message(target_user_id, "❌ Payment Rejected! Please contact support or check your UTR.")

@bot.callback_query_handler(func=lambda call: call.data in CC_PLANS.keys())
def handle_cc_purchase(call):
    user_id = call.from_user.id
    plan_key = call.data
    plan = CC_PLANS.get(plan_key)
    user_balance = USERS.get(user_id, {}).get('balance', 0.0)
    
    try:
        price_val = float(plan['price'])
    except:
        price_val = 0.0
    
    markup = InlineKeyboardMarkup()
    if user_balance >= price_val and price_val > 0:
        markup.add(InlineKeyboardButton("✅ Confirm & Purchase Now", callback_data=f'confirmcc_{plan_key}'))
    elif price_val == 0:
        markup.add(InlineKeyboardButton("💬 Contact Admin for Custom Pack", url="https://t.me/YourAdminUsername"))
    else:
        markup.add(InlineKeyboardButton("❌ Insufficient Balance (Add Money)", callback_data='go_add_money'))
        
    preview_msg = (
        "╔════════════════════╗\n"
        f"      📦 {plan['name']} 📦\n"
        "╚════════════════════╝\n\n"
        f"💎 Value: {plan['value']}\n"
        f"💰 Price: {plan['display_price']}\n"
        f"👛 Your Wallet: ₹{user_balance}\n\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(call.message.chat.id, preview_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirmcc_'))
def confirm_cc_purchase(call):
    user_id = call.from_user.id
    plan_key = call.data.replace('confirmcc_', '')
    plan = CC_PLANS.get(plan_key)
    
    price_val = float(plan['price'])
    user_data = USERS.get(user_id, {'balance': 0.0, 'referred_by': None})
    
    if user_data['balance'] < price_val:
        bot.answer_callback_query(call.id, "❌ Error: Insufficient balance in wallet!", show_alert=True)
        return
    
    USERS[user_id]['balance'] -= price_val
    
    referred_by = user_data.get('referred_by')
    if referred_by and referred_by in USERS:
        commission = price_val * 0.20
        USERS[referred_by]['balance'] += commission
        bot.send_message(referred_by, f"🎁 Commission Earned! Aapke referred user ne plan buy kiya aur aapko ₹{commission} (20%) commission mila hai!")

    PURCHASE_HISTORY.append({'user_id': user_id, 'plan': plan['name'], 'price': plan['display_price']})
    
    success_msg = (
        "╔════════════════════╗\n"
        "   📦 PURCHASE SUCCESSFUL 📦\n"
        "╚════════════════════╝\n\n"
        f"📦 Plan: {plan['name']}\n"
        f"💎 Value: {plan['value']}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"Here is your CC Data:\n{plan['details']}\n\n"
        "⚠️ Save this data securely!"
    )
    bot.send_message(call.message.chat.id, success_msg)
    bot.send_message(ADMIN_ID, f"🔔 New CC Store Order!\nUser ID: {user_id} bought: {plan['name']} ({plan['display_price']})")

@bot.callback_query_handler(func=lambda call: call.data in LIKE_PLANS.keys())
def handle_like_purchase(call):
    user_id = call.from_user.id
    plan_key = call.data
    plan = LIKE_PLANS.get(plan_key)
    user_balance = USERS.get(user_id, {}).get('balance', 0.0)
    
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
        f"      📦 {plan['name']} 📦\n"
        "╚════════════════════╝\n\n"
        f"{plan['details']}\n\n"
        f"💰 Price: {plan['display_price']}\n"
        f"👛 Your Wallet: ₹{user_balance}\n\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(call.message.chat.id, preview_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirmlike_'))
def confirm_like_purchase(call):
    user_id = call.from_user.id
    plan_key = call.data.replace('confirmlike_', '')
    plan = LIKE_PLANS.get(plan_key)
    
    price_val = float(plan['price'])
    user_data = USERS.get(user_id, {'balance': 0.0, 'referred_by': None})
    
    if user_data['balance'] < price_val:
        bot.answer_callback_query(call.id, "❌ Error: Insufficient balance in wallet!", show_alert=True)
        return
    
    USERS[user_id]['balance'] -= price_val

    referred_by = user_data.get('referred_by')
    if referred_by and referred_by in USERS:
        commission = price_val * 0.20
        USERS[referred_by]['balance'] += commission
        bot.send_message(referred_by, f"🎁 Commission Earned! Aapke referred user ne Like Pack buy kiya aur aapko ₹{commission} (20%) commission mila hai!")

    expiry_date = (datetime.now() + timedelta(days=plan['days'])).strftime("%d-%m-%Y %H:%M")
    
    USERS[user_id]['active_plans'].append({
        'name': f"{plan['name']} ({plan['total']} Likes)",
        'expiry': expiry_date
    })
    
    PURCHASE_HISTORY.append({'user_id': user_id, 'plan': plan['name'], 'price': plan['display_price']})
    
    success_msg = (
        "╔════════════════════╗\n"
        "   🎉 ORDER SUCCESSFUL 🎉\n"
        "╚════════════════════╝\n\n"
        f"📦 Plan: {plan['name']}\n"
        f"❤️ Total Likes: {plan['total']} ({plan['daily']} Daily)\n"
        f"📅 Valid Till: {expiry_date}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🛡️ Your active plan has been saved! Check 'My Active Plans'."
    )
    bot.send_message(call.message.chat.id, success_msg)
    bot.send_message(ADMIN_ID, f"🔔 New Like Store Order!\nUser ID: {user_id} bought: {plan['name']} ({plan['display_price']})")

if __name__ == '__main__':
    print("💎 CC & Like Store Bot is running successfully...")
    keep_alive()
    bot.infinity_polling()
