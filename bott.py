import os
from flask import Flask
from threading import Thread
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

TOKEN = '8878169821:AAGRH_IDrgb-Hyan5O9LX76-JLMYJ87Gd_Y'
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

SETTINGS = {'refer_reward': 5.0}

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
        USERS[user_id] = {'balance': 0.0, 'referrals': 0, 'referred_by': None, 'active_plans': [], 'referred_users': []}
    return USERS[user_id]

def main_reply_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("🛒 CC Store"), KeyboardButton("❤️ Like Store"),
        KeyboardButton("👛 My Wallet"), KeyboardButton("➕ Add Money"),
        KeyboardButton("👥 Refer & Earn"), KeyboardButton("🛠️ Support"),
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

    bot.send_message(message.chat.id, "🚀 *Access Granted!* Welcome to the VIP dashboard. Use the keyboard below:", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'verify_join')
def verify_join(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.send_message(call.message.chat.id, "🚀 *Verification Successful!* Welcome to the VIP dashboard. Use the keyboard below:", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
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
                get_user(target_user_id)['balance'] += amount
                ADMIN_STATE.pop(user_id, None)
                bot.send_message(message.chat.id, f"✅ Successfully added **₹{amount}** to User ID: `{target_user_id}`!", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
                bot.send_message(target_user_id, f"🎉 *Good News!* Admin has added **₹{amount}** to your wallet.", parse_mode='Markdown')
            except ValueError:
                bot.send_message(message.chat.id, "❌ *Invalid amount!*", parse_mode='Markdown')
            return
        elif state == 'edit_cc_price':
            plan_key = ADMIN_STATE[user_id].get('plan_key')
            if plan_key in CC_PLANS:
                CC_PLANS[plan_key]['display_price'] = text
                CC_PLANS[plan_key]['price'] = ''.join([c for c in text if c.isdigit()]) or "0"
            ADMIN_STATE.pop(user_id, None)
            bot.send_message(message.chat.id, f"✅ CC Plan price updated to *{text}*!", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
            return
        elif state == 'edit_cc_details':
            plan_key = ADMIN_STATE[user_id].get('plan_key')
            if plan_key in CC_PLANS:
                CC_PLANS[plan_key]['details'] = text
            ADMIN_STATE.pop(user_id, None)
            bot.send_message(message.chat.id, f"✅ CC Plan details updated!", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
            return
        elif state == 'edit_like_price':
            plan_key = ADMIN_STATE[user_id].get('plan_key')
            if plan_key in LIKE_PLANS:
                LIKE_PLANS[plan_key]['display_price'] = text
                LIKE_PLANS[plan_key]['price'] = ''.join([c for c in text if c.isdigit()]) or "0"
            ADMIN_STATE.pop(user_id, None)
            bot.send_message(message.chat.id, f"✅ Like Pack price updated to *{text}*!", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
            return
        elif state == 'edit_like_details':
            plan_key = ADMIN_STATE[user_id].get('plan_key')
            if plan_key in LIKE_PLANS:
                LIKE_PLANS[plan_key]['details'] = text
            ADMIN_STATE.pop(user_id, None)
            bot.send_message(message.chat.id, f"✅ Like Pack details updated!", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
            return

    if user_id in USER_STATE and USER_STATE[user_id].get('state') == 'waiting_for_amount':
        if not text.isdigit():
            bot.send_message(message.chat.id, "❌ *Error:* Please enter valid amount in numbers.", parse_mode='Markdown')
            return
        try:
            amount = float(text)
            if amount <= 0: raise ValueError()
            USER_STATE[user_id] = {'state': 'waiting_for_utr', 'amount': amount}
            pay_text = (
                "💎 **SECURE PAYMENT GATEWAY**\n\n"
                f"💵 Amount to Pay: **₹{amount}**\n"
                "🎯 UPI ID: `sima6241@ptaxis`\n\n"
                "📌 *Instructions:*\n1. Pay via UPI.\n2. Send 12-digit UTR ID here."
            )
            bot.send_message(message.chat.id, pay_text, parse_mode='Markdown')
        except ValueError:
            bot.send_message(message.chat.id, "❌ *Please enter valid numbers.*", parse_mode='Markdown')
        return

    elif user_id in USER_STATE and USER_STATE[user_id].get('state') == 'waiting_for_utr':
        utr, amount = text, USER_STATE[user_id]['amount']
        USER_STATE.pop(user_id, None)
        bot.send_message(message.chat.id, "✅ *Proof Submitted Successfully!*", reply_markup=main_reply_keyboard(user_id), parse_mode='Markdown')
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{amount}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}"))
        bot.send_message(ADMIN_ID, f"🔔 **NEW PAYMENT PROOF**\n\n👤 User: {username} (`{user_id}`)\n💵 Amount: ₹{amount}\n🧾 UTR: `{utr}`", reply_markup=markup, parse_mode='Markdown')
        return

    if text == "🛒 CC Store":
        markup = InlineKeyboardMarkup(row_width=1)
        for key, plan in CC_PLANS.items():
            markup.add(InlineKeyboardButton(f"⚡ {plan['name']} ➔ {plan['display_price']} ({plan['value']})", callback_data=key))
        bot.send_message(message.chat.id, "💎 **CC STORE**\n⭐ Rating: `4.9/5`", reply_markup=markup, parse_mode='Markdown')

    elif text == "❤️ Like Store":
        markup = InlineKeyboardMarkup(row_width=1)
        for key, plan in LIKE_PLANS.items():
            markup.add(InlineKeyboardButton(f"⚡ {plan['name']} ➔ {plan['display_price']}", callback_data=key))
        bot.send_message(message.chat.id, "❤️ **LIKE STORE**\n⭐ Rating: `5.0/5`", reply_markup=markup, parse_mode='Markdown')

    elif text == "📦 My Active Plans":
        active_plans = user_data.get('active_plans', [])
        if not active_plans:
            bot.send_message(message.chat.id, "📦 *Aapka koi active plan nahi hai!*", parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))
        else:
            msg = "📦 **YOUR ACTIVE PLANS:**\n\n"
            for p in active_plans: msg += f"🔹 **{p['name']}**\n📅 Expires: `{p['expiry']}`\n\n"
            bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))

    elif text == "👛 My Wallet":
        bot.send_message(message.chat.id, f"👛 **VIP WALLET**\n\n🆔 UID: `{user_id}`\n💰 Balance: **₹{user_data['balance']}**\n👥 Referrals: **{user_data['referrals']} Users**", parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))

    elif text == "➕ Add Money":
        USER_STATE[user_id] = {'state': 'waiting_for_amount'}
        bot.send_message(message.chat.id, "➕ **ADD MONEY**\n\n💵 *Kitna amount add karna hai? (Numbers only):*", parse_mode='Markdown')

    elif text == "👥 Refer & Earn":
        bot_uname = bot.get_me().username
        ref_link = f"https://t.me/{bot_uname}?start=ref_{user_id}"
        ref_list = "\n".join([f"• `{uid}`" for uid in user_data['referred_users']]) if user_data['referred_users'] else "Aapne abhi tak kisi ko refer nahi kiya."
        bot.send_message(message.chat.id, f"🎁 **REFER & EARN**\n\nBonus: **₹{SETTINGS['refer_reward']}** per refer!\nTotal Referrals: **{user_data['referrals']}**\n{ref_list}\n\n🔗 Link:\n`{ref_link}`", parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))

    elif text == "🛠️ Support":
        bot.send_message(message.chat.id, "🛠️ **SUPPORT**\n\n💬 Admin: `@Xenon_ask9`\n🌐 Website: [Click Here](https://web-cc-4.onrender.com/products)", parse_mode='Markdown', reply_markup=main_reply_keyboard(user_id))

    elif text == "👑 Admin Panel" and user_id == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("➕ Add Balance", callback_data='admin_add_money'), InlineKeyboardButton("⚙️ Edit Prices/Details", callback_data='admin_edit_prices'), InlineKeyboardButton("📊 Stats", callback_data='admin_stats'))
        bot.send_message(message.chat.id, "👑 **ADMIN PANEL**", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_') or call.data.startswith('edit_'))
def handle_admin_panels(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID: return
    if call.data == 'admin_add_money':
        if user_id not in ADMIN_STATE: ADMIN_STATE[user_id] = {}
        ADMIN_STATE[user_id]['action'] = 'add_bal_get_id'
        bot.send_message(call.message.chat.id, "📥 *Enter Target User ID*:", parse_mode='Markdown')
    elif call.data == 'admin_edit_prices':
        markup = InlineKeyboardMarkup(row_width=1)
        for key, plan in CC_PLANS.items():
            markup.add(InlineKeyboardButton(f"💵 CC: {plan['name']} Price", callback_data=f"editccprice_{key}"), InlineKeyboardButton(f"📝 CC: {plan['name']} Details", callback_data=f"editccdetails_{key}"))
        for key, plan in LIKE_PLANS.items():
            markup.add(InlineKeyboardButton(f"💵 Like: {plan['name']} Price", callback_data=f"editlikeprice_{key}"), InlineKeyboardButton(f"📝 Like: {plan['name']} Details", callback_data=f"editlikedetails_{key}"))
        bot.send_message(call.message.chat.id, "⚙️ *Select to edit:*", reply_markup=markup, parse_mode='Markdown')
    elif call.data == 'admin_stats':
        tot_bal = sum([u['balance'] for u in USERS.values()])
        bot.send_message(call.message.chat.id, f"📊 **Stats:**\nUsers: {len(USERS)}\nBalances: ₹{tot_bal}\nPurchases: {len(PURCHASE_HISTORY)}", parse_mode='Markdown')
    elif call.data.startswith('editccprice_'):
        if user_id not in ADMIN_STATE: ADMIN_STATE[user_id] = {}
        ADMIN_STATE[user_id].update({'action': 'edit_cc_price', 'plan_key': call.data.split('_')[1]})
        bot.send_message(call.message.chat.id, "💵 Enter new CC price (e.g. ₹149):", parse_mode='Markdown')
    elif call.data.startswith('editccdetails_'):
        if user_id not in ADMIN_STATE: ADMIN_STATE[user_id] = {}
        ADMIN_STATE[user_id].update({'action': 'edit_cc_details', 'plan_key': call.data.split('_')[1]})
        bot.send_message(call.message.chat.id, "📝 Enter new CC details layout:", parse_mode='Markdown')
    elif call.data.startswith('editlikeprice_'):
        if user_id not in ADMIN_STATE: ADMIN_STATE[user_id] = {}
        ADMIN_STATE[user_id].update({'action': 'edit_like_price', 'plan_key': call.data.split('_')[1]})
        bot.send_message(call.message.chat.id, "💵 Enter new Like price (e.g. ₹99):", parse_mode='Markdown')
    elif call.data.startswith('editlikedetails_'):
        if user_id not in ADMIN_STATE: ADMIN_STATE[user_id] = {}
        ADMIN_STATE[user_id].update({'action': 'edit_like_details', 'plan_key': call.data.split('_')[1]})
        bot.send_message(call.message.chat.id, "📝 Enter new Like description:", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_') or call.data.startswith('reject_'))
def handle_payment_approval(call):
    if call.from_user.id != ADMIN_ID: return
    data = call.data.split('_')
    action, target_user_id = data[0], int(data[1])
    if action == 'approve':
        amount = float(data[2])
        get_user(target_user_id)['balance'] += amount
        try: bot.edit_message_text(f"✅ Approved ₹{amount} for `{target_user_id}`", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        except: pass
        bot.send_message(target_user_id, f"🎉 Payment Approved! ₹{amount} added.", parse_mode='Markdown')
    elif action == 'reject':
        try: bot.edit_message_text(f"❌ Payment Rejected for `{target_user_id}`", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        except: pass
        bot.send_message(target_user_id, "❌ Payment Rejected!", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data in CC_PLANS.keys())
def handle_cc_purchase(call):
    user_id = call.from_user.id
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ Pehle channels join karein!", show_alert=True)
        return
    plan = CC_PLANS.get(call.data)
    bal = get_user(user_id)['balance']
    price = float(plan['price'])
    markup = InlineKeyboardMarkup()
    if bal >= price and price > 0: markup.add(InlineKeyboardButton("✅ Confirm", callback_data=f"confirmcc_{call.data}"))
    elif price == 0: markup.add(InlineKeyboardButton("💬 Contact Admin", url="https://t.me/Xenon_ask9"))
    else: markup.add(InlineKeyboardButton("❌ Insufficient Balance", callback_data="go"))
    bot.send_message(call.message.chat.id, f"📦 **{plan['name']}**\nPrice: {plan['display_price']}\nWallet: ₹{bal}", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirmcc_'))
def confirm_cc_purchase(call):
    user_id = call.from_user.id
    plan = CC_PLANS.get(call.data.replace('confirmcc_', ''))
    u_data = get_user(user_id)
    price = float(plan['price'])
    if u_data['balance'] < price: return
    u_data['balance'] -= price
    if u_data['referred_by']:
        get_user(u_data['referred_by'])['balance'] += price * 0.20
    PURCHASE_HISTORY.append({'user_id': user_id, 'plan': plan['name'], 'price': plan['display_price']})
    bot.send_message(call.message.chat.id, f"📦 **SUCCESS**\n\n{plan['details']}", parse_mode='Markdown')
    bot.send_message(ADMIN_ID, f"🔔 New CC Order from `{user_id}`", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data in LIKE_PLANS.keys())
def handle_like_purchase(call):
    user_id = call.from_user.id
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id, "❌ Pehle channels join karein!", show_alert=True)
        return
    plan = LIKE_PLANS.get(call.data)
    bal = get_user(user_id)['balance']
    price = float(plan['price'])
    markup = InlineKeyboardMarkup()
    if bal >= price: markup.add(InlineKeyboardButton("✅ Confirm", callback_data=f"confirmlike_{call.data}"))
    else: markup.add(InlineKeyboardButton("❌ Insufficient Balance", callback_data="go"))
    bot.send_message(call.message.chat.id, f"📦 **{plan['name']}**\n{plan['details']}\nPrice: {plan['display_price']}\nWallet: ₹{bal}", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirmlike_'))
def confirm_like_purchase(call):
    user_id = call.from_user.id
    plan = LIKE_PLANS.get(call.data.replace('confirmlike_', ''))
    u_data = get_user(user_id)
    price = float(plan['price'])
    if u_data['balance'] < price: return
    u_data['balance'] -= price
    if u_data['referred_by']:
        get_user(u_data['referred_by'])['balance'] += price * 0.20
    expiry = (datetime.now() + timedelta(days=plan['days'])).strftime("%d-%m-%Y %H:%M")
    u_data['active_plans'].append({'name': f"{plan['name']} ({plan['total']} Likes)", 'expiry': expiry})
    PURCHASE_HISTORY.append({'user_id': user_id, 'plan': plan['name'], 'price': plan['display_price']})
    bot.send_message(call.message.chat.id, f"🎉 **ORDER SUCCESSFUL**\nValid Till: `{expiry}`", parse_mode='Markdown')
    bot.send_message(ADMIN_ID, f"🔔 New Like Order from `{user_id}`", parse_mode='Markdown')

if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling()                                                                                          
                                                                                                           
