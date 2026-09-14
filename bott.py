import os
import sqlite3
import uuid
import asyncio
import threading
from datetime import datetime, timedelta

import requests
from flask import Flask
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.error import Forbidden, BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# CONFIG
# =========================================================

# Render Environment Variable se token lega
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN environment variable set karo.")
    

ADMIN_ID = 7161571409

UPI_ID = "sima6241@ptaxis"

DB_FILE = "vipbot.db"

SUPPORT_USERNAME = "@your_support"

REFERRAL_REWARD = 2.0

REQUIRED_CHANNELS = [
    ("Bot Like Proof", "@botlikeproof", "https://t.me/botlikeproof"),
    ("Earning With Ask 9", "@eraningwithask9", "https://t.me/eraningwithask9"),
    ("Earning With Ask", "@eraningwithask", "https://t.me/eraningwithask"),
]

INFO_API = (
    "https://star-info-api.lovable.app/"
    "functions/v1/info-api/accinfo"
)

BAN_API = (
    "https://info.killersharmabot.online/"
    "bancheck"
)

ICON_API = (
    "https://star-icon-png.lovable.app/"
    "png"
)

# =========================================================
# RENDER WEB SERVER
# =========================================================

web_app = Flask(__name__)


@web_app.get("/")
def home():
    return "VIP Bot is running ✅", 200


@web_app.get("/health")
def health():
    return "OK", 200


def run_web():
    port = int(os.getenv("PORT", "10000"))

    web_app.run(
        host="0.0.0.0",
        port=port,
        use_reloader=False
    )


# =========================================================
# DATABASE
# =========================================================

def connect():
    con = sqlite3.connect(
        DB_FILE,
        timeout=30
    )

    con.execute("PRAGMA busy_timeout=30000")

    return con


def now():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def init_db():

    con = connect()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0,
            referred_by INTEGER,
            referral_rewarded INTEGER DEFAULT 0,
            joined_gate INTEGER DEFAULT 0,
            created TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            plan_id TEXT PRIMARY KEY,
            name TEXT,
            days INTEGER,
            daily INTEGER,
            price REAL,
            active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER,
            uid TEXT,
            plan_id TEXT,
            amount REAL,
            status TEXT,
            start_time TEXT,
            expiry_time TEXT,
            created TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            deposit_id TEXT PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            utr TEXT,
            status TEXT,
            created TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            type TEXT,
            note TEXT,
            created TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cc_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT UNIQUE,
            sold INTEGER DEFAULT 0,
            sold_to INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    defaults = {
        "referral_reward": "2",
        "cc_name": "💎 Premium Digital Store",
        "cc_price": "100",
        "cc_value": "₹3,000",
        "cc_description": (
            "Premium authorized digital product\n"
            "⚡ Instant delivery\n"
            "🆔 UID not required"
        ),
    }

    for key, value in defaults.items():

        cur.execute("""
            INSERT OR IGNORE INTO settings
            (key, value)
            VALUES (?, ?)
        """, (key, value))

    plans = [
        ("demo", "❤️ Demo Like", 1, 1, 5),
        ("starter", "❤️ Starter", 15, 220, 59),
        ("pro", "🔥 Pro", 30, 220, 99),
    ]

    for plan in plans:

        cur.execute("""
            INSERT OR IGNORE INTO plans
            (plan_id, name, days, daily, price, active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, plan)

    # Existing DB migration
    cur.execute("PRAGMA table_info(orders)")

    columns = [
        x[1]
        for x in cur.fetchall()
    ]

    if "start_time" not in columns:

        cur.execute(
            "ALTER TABLE orders ADD COLUMN start_time TEXT"
        )

    if "expiry_time" not in columns:

        cur.execute(
            "ALTER TABLE orders ADD COLUMN expiry_time TEXT"
        )

    con.commit()
    con.close()


def setting(key, default=""):

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT value FROM settings WHERE key=?",
        (key,)
    )

    row = cur.fetchone()

    con.close()

    return row[0] if row else default


def set_setting(key, value):

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO settings(key,value)
        VALUES (?,?)
        ON CONFLICT(key)
        DO UPDATE SET value=excluded.value
    """, (
        key,
        str(value)
    ))

    con.commit()
    con.close()


# =========================================================
# USER / WALLET
# =========================================================

def create_user(user_id, username=""):

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO users
        (user_id, username, created)
        VALUES (?, ?, ?)
    """, (
        user_id,
        username,
        now()
    ))

    cur.execute("""
        UPDATE users
        SET username=?
        WHERE user_id=?
    """, (
        username,
        user_id
    ))

    con.commit()
    con.close()


def get_balance(user_id):

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    )

    row = cur.fetchone()

    con.close()

    return float(row[0]) if row else 0.0


def credit(user_id, amount, note):

    con = connect()
    cur = con.cursor()

    cur.execute("""
        UPDATE users
        SET balance=balance+?
        WHERE user_id=?
    """, (
        amount,
        user_id
    ))

    cur.execute("""
        INSERT INTO transactions
        (user_id, amount, type, note, created)
        VALUES (?, ?, 'CREDIT', ?, ?)
    """, (
        user_id,
        amount,
        note,
        now()
    ))

    con.commit()
    con.close()


def debit(user_id, amount, note):

    con = connect()
    cur = con.cursor()

    # IMPORTANT:
    # Balance negative nahi hone dena.
    cur.execute("""
        UPDATE users
        SET balance=balance-?
        WHERE user_id=?
        AND balance>=?
    """, (
        amount,
        amount,
        amount
    ))

    changed = cur.rowcount

    if changed != 1:

        con.rollback()
        con.close()

        return False

    cur.execute("""
        INSERT INTO transactions
        (user_id, amount, type, note, created)
        VALUES (?, ?, 'DEBIT', ?, ?)
    """, (
        user_id,
        -amount,
        note,
        now()
    ))

    con.commit()
    con.close()

    return True


# =========================================================
# STATE
# =========================================================

def clear_state(context):
    context.user_data.clear()


# =========================================================
# CHANNEL JOIN
# =========================================================

async def check_channels(user_id, bot):

    missing = []

    for name, username, link in REQUIRED_CHANNELS:

        try:

            member = await bot.get_chat_member(
                username,
                user_id
            )

            if member.status in (
                "left",
                "kicked"
            ):

                missing.append(
                    (name, link)
                )

        except Exception:

            missing.append(
                (name, link)
            )

    return missing


async def show_join_gate(update, context):

    buttons = []

    for name, username, link in REQUIRED_CHANNELS:

        buttons.append([
            InlineKeyboardButton(
                f"📢 JOIN {name.upper()}",
                url=link
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "✅ CHECK JOIN",
            callback_data="check_join"
        )
    ])

    text = (
        "╔════════════════════════════╗\n"
        "       🔐 VIP ACCESS LOCKED\n"
        "╚════════════════════════════╝\n\n"
        "Bot start karne ke liye pehle "
        "required channels join karo.\n\n"
        "👇 Join ke baad CHECK JOIN dabao."
    )

    if update.message:

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    else:

        await update.callback_query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def is_verified(update, context):

    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        return True

    missing = await check_channels(
        user_id,
        context.bot
    )

    if missing:

        await show_join_gate(
            update,
            context
        )

        return False

    create_user(
        user_id,
        update.effective_user.username or ""
    )

    con = connect()
    cur = con.cursor()

    cur.execute("""
        UPDATE users
        SET joined_gate=1
        WHERE user_id=?
    """, (user_id,))

    cur.execute("""
        SELECT referred_by, referral_rewarded
        FROM users
        WHERE user_id=?
    """, (user_id,))

    row = cur.fetchone()

    if row:

        referred_by, rewarded = row

        if referred_by and not rewarded:

            reward = float(
                setting(
                    "referral_reward",
                    "2"
                )
            )

            cur.execute("""
                UPDATE users
                SET referral_rewarded=1
                WHERE user_id=?
            """, (user_id,))

            cur.execute("""
                UPDATE users
                SET balance=balance+?
                WHERE user_id=?
            """, (
                reward,
                referred_by
            ))

            cur.execute("""
                INSERT INTO transactions
                (user_id, amount, type, note, created)
                VALUES (?, ?, 'CREDIT', ?, ?)
            """, (
                referred_by,
                reward,
                "Referral Reward",
                now()
            ))

            con.commit()

            try:

                await context.bot.send_message(
                    referred_by,
                    "🎉 **REFERRAL VERIFIED!**\n\n"
                    f"💰 Reward: ₹{reward:g}\n"
                    f"💵 Balance: ₹{get_balance(referred_by):.2f}",
                    parse_mode="Markdown"
                )

            except Exception:
                pass

    con.commit()
    con.close()

    return True


# =========================================================
# KEYBOARD
# =========================================================

def main_keyboard():

    return ReplyKeyboardMarkup(
        [
            ["❤️ Buy Like", "🛒 CC Store"],
            ["🔍 Check UID", "💰 Wallet"],
            ["👥 Refer & Earn", "➕ Add Money"],
            ["📦 My Orders", "🆘 Support"],
        ],
        resize_keyboard=True
    )


# =========================================================
# START
# =========================================================

async def start(update, context):

    user = update.effective_user

    create_user(
        user.id,
        user.username or ""
    )

    if context.args and context.args[0].isdigit():

        ref_id = int(context.args[0])

        if ref_id != user.id:

            con = connect()
            cur = con.cursor()

            cur.execute("""
                SELECT referred_by
                FROM users
                WHERE user_id=?
            """, (user.id,))

            row = cur.fetchone()

            if row and row[0] is None:

                cur.execute("""
                    UPDATE users
                    SET referred_by=?
                    WHERE user_id=?
                """, (
                    ref_id,
                    user.id
                ))

            con.commit()
            con.close()

    if not await is_verified(
        update,
        context
    ):
        return

    clear_state(context)

    await update.message.reply_text(
        "╔════════════════════════════╗\n"
        "          👑 VIP STORE\n"
        "╚════════════════════════════╝\n\n"
        "✨ Premium Service Panel\n"
        "⚡ Fast Processing\n"
        "💰 Secure Wallet\n"
        "🎁 Refer & Earn\n\n"
        "👇 Service select karo.",
        reply_markup=main_keyboard()
    )


# =========================================================
# LIKE PLANS
# =========================================================

async def buy_like(update, context):

    if not await is_verified(
        update,
        context
    ):
        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT plan_id, name, days, daily, price
        FROM plans
        WHERE active=1
        ORDER BY price
    """)

    plans = cur.fetchall()

    con.close()

    buttons = []

    for plan_id, name, days, daily, price in plans:

        buttons.append([
            InlineKeyboardButton(
                f"{name} • ₹{price:g}",
                callback_data=f"likeplan:{plan_id}"
            )
        ])

    text = (
        "╔════════════════════════════╗\n"
        "          ❤️ LIKE PLANS\n"
        "╚════════════════════════════╝\n\n"
    )

    for plan_id, name, days, daily, price in plans:

        text += (
            f"💎 {name}\n"
            f"❤️ {daily} Like/day\n"
            f"📅 {days} Day(s)\n"
            f"💰 ₹{price:g}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
        )

    text += (
        "\n⚠️ ₹5 Demo Plan:\n"
        "24 hours mein sirf 1 order allowed."
    )

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def like_plan_callback(update, context):

    q = update.callback_query

    await q.answer()

    plan_id = q.data.split(
        ":",
        1
    )[1]

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT name, days, daily, price
        FROM plans
        WHERE plan_id=? AND active=1
    """, (plan_id,))

    row = cur.fetchone()

    con.close()

    if not row:

        await q.message.reply_text(
            "❌ Plan unavailable."
        )

        return

    name, days, daily, price = row

    user_id = q.from_user.id

    # Demo cooldown
    if plan_id == "demo":

        con = connect()
        cur = con.cursor()

        since = (
            datetime.now()
            - timedelta(hours=24)
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cur.execute("""
            SELECT COUNT(*)
            FROM orders
            WHERE user_id=?
            AND plan_id='demo'
            AND created>=?
            AND status NOT IN ('Cancelled','Rejected')
        """, (
            user_id,
            since
        ))

        used = cur.fetchone()[0]

        con.close()

        if used >= 1:

            await q.message.reply_text(
                "⏳ **DEMO PLAN COOLDOWN**\n\n"
                "₹5 Demo plan 24 hours mein "
                "sirf 1 baar liya ja sakta hai.",
                parse_mode="Markdown"
            )

            return

    context.user_data.clear()

    context.user_data["like_plan"] = plan_id
    context.user_data["waiting_like_uid"] = True

    await q.message.reply_text(
        "╔════════════════════════════╗\n"
        "       📦 LIKE ORDER\n"
        "╚════════════════════════════╝\n\n"
        f"💎 {name}\n"
        f"❤️ {daily} Like/day\n"
        f"📅 {days} Day(s)\n"
        f"💰 ₹{price:g}\n\n"
        "🆔 **Ab sirf game UID bhejo.**\n\n"
        "⚠️ UTR yahan mat bhejna.",
        parse_mode="Markdown"
    )


async def like_uid_handler(update, context):

    uid = update.message.text.strip()

    if not uid.isdigit():

        await update.message.reply_text(
            "❌ UID sirf numbers mein bhejo."
        )

        return

    plan_id = context.user_data.get(
        "like_plan"
    )

    if not plan_id:

        clear_state(context)

        await update.message.reply_text(
            "❌ Order session expired.\n"
            "❤️ Buy Like se dobara start karo.",
            reply_markup=main_keyboard()
        )

        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT name, days, daily, price
        FROM plans
        WHERE plan_id=? AND active=1
    """, (plan_id,))

    row = cur.fetchone()

    con.close()

    if not row:

        clear_state(context)

        return

    name, days, daily, price = row

    user_id = update.effective_user.id

    balance = get_balance(user_id)

    if balance < price:

        clear_state(context)

        await update.message.reply_text(
            "❌ **LOW WALLET BALANCE**\n\n"
            f"💰 Required: ₹{price:g}\n"
            f"💵 Balance: ₹{balance:.2f}\n\n"
            "➕ Add Money karke dobara try karo.",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

        return

    # Demo check again
    if plan_id == "demo":

        con = connect()
        cur = con.cursor()

        since = (
            datetime.now()
            - timedelta(hours=24)
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cur.execute("""
            SELECT COUNT(*)
            FROM orders
            WHERE user_id=?
            AND plan_id='demo'
            AND created>=?
            AND status NOT IN ('Cancelled','Rejected')
        """, (
            user_id,
            since
        ))

        used = cur.fetchone()[0]

        con.close()

        if used >= 1:

            clear_state(context)

            await update.message.reply_text(
                "⏳ Demo already used in last 24 hours.",
                reply_markup=main_keyboard()
            )

            return

    # Reserve payment immediately.
    # This prevents user from spending the same wallet
    # balance before admin approval.
    if not debit(
        user_id,
        price,
        "Reserved Like Plan Payment"
    ):

        clear_state(context)

        await update.message.reply_text(
            "❌ Wallet balance change nahi ho saka.\n"
            "Please try again.",
            reply_markup=main_keyboard()
        )

        return

    order_id = (
        "ORD-"
        + uuid.uuid4().hex[:8].upper()
    )

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO orders
        (order_id, user_id, uid, plan_id,
         amount, status, start_time,
         expiry_time, created)
        VALUES (?, ?, ?, ?, ?, 'Pending Approval',
                NULL, NULL, ?)
    """, (
        order_id,
        user_id,
        uid,
        plan_id,
        price,
        now()
    ))

    con.commit()
    con.close()

    clear_state(context)

    await update.message.reply_text(
        "╔════════════════════════════╗\n"
        "       ⏳ ORDER SUBMITTED\n"
        "╚════════════════════════════╝\n\n"
        f"🧾 Order: `{order_id}`\n"
        f"🆔 UID: `{uid}`\n"
        f"📦 Plan: {name}\n"
        f"❤️ {daily}/day\n"
        f"📅 {days} Day(s)\n"
        f"💰 Price: ₹{price:g}\n\n"
        "📌 Status: **PENDING APPROVAL**\n\n"
        "Admin approval ke baad plan activate hoga.",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

    try:

        await context.bot.send_message(
            ADMIN_ID,
            "🔔 **NEW LIKE PLAN REQUEST**\n\n"
            f"🧾 `{order_id}`\n"
            f"👤 User: `{user_id}`\n"
            f"🆔 UID: `{uid}`\n"
            f"📦 {name}\n"
            f"❤️ {daily}/day\n"
            f"📅 {days} days\n"
            f"💰 ₹{price:g}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✅ APPROVE",
                        callback_data=f"likeapprove:{order_id}"
                    ),
                    InlineKeyboardButton(
                        "❌ REJECT",
                        callback_data=f"likereject:{order_id}"
                    )
                ]
            ])
        )

    except Exception as e:

        print(
            "Admin notification error:",
            e
        )


# =========================================================
# LIKE ADMIN APPROVAL
# =========================================================

async def like_approval(update, context):

    q = update.callback_query

    if q.from_user.id != ADMIN_ID:

        await q.answer(
            "❌ Admin only.",
            show_alert=True
        )

        return

    await q.answer()

    action, order_id = q.data.split(
        ":",
        1
    )

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, uid, plan_id,
               amount, status
        FROM orders
        WHERE order_id=?
    """, (order_id,))

    row = cur.fetchone()

    if not row:

        con.close()

        await q.message.reply_text(
            "❌ Order not found."
        )

        return

    user_id, uid, plan_id, amount, status = row

    if status != "Pending Approval":

        con.close()

        await q.message.reply_text(
            "⚠️ Order already processed."
        )

        return

    # REJECT
    if action == "likereject":

        cur.execute("""
            UPDATE orders
            SET status='Rejected'
            WHERE order_id=?
        """, (order_id,))

        con.commit()
        con.close()

        # Refund reserved wallet amount
        credit(
            user_id,
            amount,
            f"Refund Like Order {order_id}"
        )

        await q.edit_message_text(
            f"❌ Order `{order_id}` rejected.\n"
            f"💰 ₹{amount:g} refunded.",
            parse_mode="Markdown"
        )

        try:

            await context.bot.send_message(
                user_id,
                "❌ **LIKE PLAN REJECTED**\n\n"
                f"🧾 Order: `{order_id}`\n"
                f"💰 Refund: ₹{amount:g}\n"
                f"💵 Balance: ₹{get_balance(user_id):.2f}",
                parse_mode="Markdown"
            )

        except Exception:
            pass

        return

    # APPROVE
    start_time = datetime.now()

    expiry = (
        start_time
        + timedelta(
            days=int(
                get_plan_days(plan_id)
            )
        )
    )

    start_str = start_time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    expiry_str = expiry.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    cur.execute("""
        UPDATE orders
        SET status='Active',
            start_time=?,
            expiry_time=?
        WHERE order_id=?
        AND status='Pending Approval'
    """, (
        start_str,
        expiry_str,
        order_id
    ))

    changed = cur.rowcount

    con.commit()
    con.close()

    if changed != 1:

        await q.message.reply_text(
            "⚠️ Order already processed."
        )

        return

    plan_name = get_plan_name(
        plan_id
    )

    await q.edit_message_text(
        "✅ **PLAN APPROVED & ACTIVATED**\n\n"
        f"🧾 `{order_id}`\n"
        f"👤 `{user_id}`\n"
        f"🆔 `{uid}`\n"
        f"📦 {plan_name}\n"
        f"💰 ₹{amount:g}\n"
        f"⏰ Expiry: `{expiry_str}`",
        parse_mode="Markdown"
    )

    try:

        await context.bot.send_message(
            user_id,
            "╔════════════════════════════╗\n"
            "       🎉 PLAN ACTIVATED\n"
            "╚════════════════════════════╝\n\n"
            f"🧾 Order: `{order_id}`\n"
            f"🆔 UID: `{uid}`\n"
            f"📦 Plan: {plan_name}\n"
            f"💰 Paid: ₹{amount:g}\n\n"
            f"🟢 Start: `{start_str}`\n"
            f"🔴 Expires: `{expiry_str}`\n\n"
            "📌 Status: **ACTIVE**",
            parse_mode="Markdown"
        )

    except Exception:
        pass


def get_plan_name(plan_id):

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT name FROM plans WHERE plan_id=?",
        (plan_id,)
    )

    row = cur.fetchone()

    con.close()

    return row[0] if row else plan_id


def get_plan_days(plan_id):

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT days FROM plans WHERE plan_id=?",
        (plan_id,)
    )

    row = cur.fetchone()

    con.close()

    return int(row[0]) if row else 1


# =========================================================
# ADD MONEY
# =========================================================

async def add_money(update, context):

    if not await is_verified(
        update,
        context
    ):
        return

    clear_state(context)

    context.user_data["deposit_amount"] = True

    # Callback se aane par update.message None hota hai.
    message = (
        update.message
        if update.message
        else update.callback_query.message
    )

    await message.reply_text(
        "╔════════════════════════════╗\n"
        "          ➕ ADD MONEY\n"
        "╚════════════════════════════╝\n\n"
        f"💳 UPI ID:\n`{UPI_ID}`\n\n"
        "💰 Amount bhejo.\n"
        "Example: `100`\n\n"
        "Payment ke baad UTR submit karna hoga.",
        parse_mode="Markdown"
    )


async def deposit_amount_handler(update, context):

    try:

        amount = float(
            update.message.text.strip()
        )

    except ValueError:

        await update.message.reply_text(
            "❌ Valid amount bhejo.\nExample: 100"
        )

        return

    if amount <= 0:

        await update.message.reply_text(
            "❌ Amount 0 se zyada hona chahiye."
        )

        return

    clear_state(context)

    context.user_data["waiting_utr"] = True
    context.user_data["deposit_value"] = amount

    await update.message.reply_text(
        "╔════════════════════════════╗\n"
        "        💳 PAYMENT STEP\n"
        "╚════════════════════════════╝\n\n"
        f"💰 Amount: ₹{amount:.2f}\n"
        f"💳 UPI: `{UPI_ID}`\n\n"
        "Payment complete karne ke baad "
        "**UTR / Transaction ID** bhejo.",
        parse_mode="Markdown"
    )


async def utr_handler(update, context):

    utr = update.message.text.strip()

    amount = context.user_data.get(
        "deposit_value"
    )

    if amount is None:

        clear_state(context)

        await update.message.reply_text(
            "❌ Deposit session expired."
        )

        return

    if len(utr) < 4:

        await update.message.reply_text(
            "❌ Valid UTR bhejo."
        )

        return

    user_id = update.effective_user.id

    deposit_id = (
        "DEP-"
        + uuid.uuid4().hex[:8].upper()
    )

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO deposits
        (deposit_id, user_id, amount,
         utr, status, created)
        VALUES (?, ?, ?, ?, 'pending', ?)
    """, (
        deposit_id,
        user_id,
        amount,
        utr,
        now()
    ))

    con.commit()
    con.close()

    clear_state(context)

    await update.message.reply_text(
        "╔════════════════════════════╗\n"
        "       🧾 UTR SUBMITTED\n"
        "╚════════════════════════════╝\n\n"
        f"🧾 Request: `{deposit_id}`\n"
        f"💰 Amount: ₹{amount:.2f}\n"
        f"🔢 UTR: `{utr}`\n\n"
        "⏳ Admin verification pending.",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

    try:

        await context.bot.send_message(
            ADMIN_ID,
            "🔔 **NEW UTR REQUEST**\n\n"
            f"🧾 `{deposit_id}`\n"
            f"👤 User: `{user_id}`\n"
            f"💰 ₹{amount:.2f}\n"
            f"🔢 UTR: `{utr}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✅ APPROVE",
                        callback_data=f"depositapprove:{deposit_id}"
                    ),
                    InlineKeyboardButton(
                        "❌ REJECT",
                        callback_data=f"depositreject:{deposit_id}"
                    )
                ]
            ])
        )

    except Exception as e:

        print(
            "UTR admin notification error:",
            e
        )


# =========================================================
# DEPOSIT APPROVAL
# =========================================================

async def deposit_action(update, context):

    q = update.callback_query

    if q.from_user.id != ADMIN_ID:

        await q.answer(
            "❌ Admin only.",
            show_alert=True
        )

        return

    await q.answer()

    action, deposit_id = q.data.split(
        ":",
        1
    )

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, amount, utr, status
        FROM deposits
        WHERE deposit_id=?
    """, (deposit_id,))

    row = cur.fetchone()

    if not row:

        con.close()

        await q.message.reply_text(
            "❌ Deposit not found."
        )

        return

    user_id, amount, utr, status = row

    if status != "pending":

        con.close()

        await q.message.reply_text(
            "⚠️ Already processed."
        )

        return

    if action == "depositreject":

        cur.execute("""
            UPDATE deposits
            SET status='rejected'
            WHERE deposit_id=?
            AND status='pending'
        """, (deposit_id,))

        con.commit()
        con.close()

        await q.edit_message_text(
            f"❌ Deposit `{deposit_id}` rejected.",
            parse_mode="Markdown"
        )

        try:

            await context.bot.send_message(
                user_id,
                "❌ **PAYMENT REJECTED**\n\n"
                f"🧾 `{deposit_id}`\n"
                "Agar payment successful thi to support se contact karo.",
                parse_mode="Markdown"
            )

        except Exception:
            pass

        return

    cur.execute("""
        UPDATE deposits
        SET status='approved'
        WHERE deposit_id=?
        AND status='pending'
    """, (deposit_id,))

    changed = cur.rowcount

    con.commit()
    con.close()

    if changed != 1:

        await q.message.reply_text(
            "⚠️ Already processed."
        )

        return

    credit(
        user_id,
        amount,
        f"UTR Approved {deposit_id}"
    )

    await q.edit_message_text(
        "✅ **PAYMENT APPROVED**\n\n"
        f"🧾 `{deposit_id}`\n"
        f"👤 `{user_id}`\n"
        f"💰 ₹{amount:.2f}",
        parse_mode="Markdown"
    )

    try:

        await context.bot.send_message(
            user_id,
            "╔════════════════════════════╗\n"
            "       💰 WALLET CREDITED\n"
            "╚════════════════════════════╝\n\n"
            f"➕ Added: ₹{amount:.2f}\n"
            f"💵 Balance: ₹{get_balance(user_id):.2f}",
        )

    except Exception:
        pass


# =========================================================
# WALLET
# =========================================================

async def wallet(update, context):

    if not await is_verified(
        update,
        context
    ):
        return

    user_id = update.effective_user.id

    await update.message.reply_text(
        "╔════════════════════════════╗\n"
        "           💰 MY WALLET\n"
        "╚════════════════════════════╝\n\n"
        f"💵 Balance: ₹{get_balance(user_id):.2f}\n\n"
        "👇 Select option:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "➕ Add Money",
                    callback_data="wallet_add"
                )
            ],
            [
                InlineKeyboardButton(
                    "🧾 History",
                    callback_data="wallet_history"
                )
            ]
        ])
    )


async def wallet_callback(update, context):

    q = update.callback_query

    await q.answer()

    if q.data == "wallet_add":

        # FIX:
        # callback query mein update.message nahi hota.
        await add_money(
            update,
            context
        )

    elif q.data == "wallet_history":

        user_id = q.from_user.id

        con = connect()
        cur = con.cursor()

        cur.execute("""
            SELECT amount, note, created
            FROM transactions
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT 15
        """, (user_id,))

        rows = cur.fetchall()

        con.close()

        if not rows:

            await q.message.reply_text(
                "🧾 No transactions yet."
            )

            return

        text = (
            "╔════════════════════════════╗\n"
            "       🧾 WALLET HISTORY\n"
            "╚════════════════════════════╝\n\n"
        )

        for amount, note, created in rows:

            text += (
                f"{'➕' if amount >= 0 else '➖'} "
                f"₹{abs(amount):.2f}\n"
                f"📌 {note}\n"
                f"🕐 {created}\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
            )

        await q.message.reply_text(
            text
        )


# =========================================================
# MY ORDERS
# =========================================================

async def my_orders(update, context):

    if not await is_verified(
        update,
        context
    ):
        return

    user_id = update.effective_user.id

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT order_id, uid, plan_id,
               amount, status,
               start_time, expiry_time
        FROM orders
        WHERE user_id=?
        ORDER BY created DESC
        LIMIT 20
    """, (user_id,))

    rows = cur.fetchall()

    con.close()

    if not rows:

        await update.message.reply_text(
            "📦 No orders yet."
        )

        return

    text = (
        "╔════════════════════════════╗\n"
        "            📦 MY ORDERS\n"
        "╚════════════════════════════╝\n\n"
    )

    for (
        order_id,
        uid,
        plan_id,
        amount,
        status,
        start_time,
        expiry_time
    ) in rows:

        plan_name = get_plan_name(
            plan_id
        )

        display_status = status

        if (
            status == "Active"
            and expiry_time
        ):

            try:

                expiry = datetime.strptime(
                    expiry_time,
                    "%Y-%m-%d %H:%M:%S"
                )

                if datetime.now() >= expiry:

                    display_status = "Expired"

                    con2 = connect()
                    cur2 = con2.cursor()

                    cur2.execute("""
                        UPDATE orders
                        SET status='Expired'
                        WHERE order_id=?
                    """, (order_id,))

                    con2.commit()
                    con2.close()

            except Exception:
                pass

        text += (
            f"🧾 `{order_id}`\n"
            f"📦 {plan_name}\n"
            f"🆔 UID: `{uid}`\n"
            f"💰 ₹{amount:g}\n"
            f"📌 {display_status}\n"
        )

        if start_time:
            text += (
                f"🟢 Start: `{start_time}`\n"
            )

        if expiry_time:
            text += (
                f"🔴 Expiry: `{expiry_time}`\n"
            )

        text += (
            "━━━━━━━━━━━━━━━━━━━━\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="Markdown"
    )


# =========================================================
# REFERRAL
# =========================================================

async def referral(update, context):

    if not await is_verified(
        update,
        context
    ):
        return

    user_id = update.effective_user.id

    me = await context.bot.get_me()

    link = (
        f"https://t.me/{me.username}"
        f"?start={user_id}"
    )

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE referred_by=?
        AND joined_gate=1
    """, (user_id,))

    refs = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE referred_by=?
        AND referral_rewarded=1
    """, (user_id,))

    rewarded = cur.fetchone()[0]

    con.close()

    reward = setting(
        "referral_reward",
        "2"
    )

    await update.message.reply_text(
        "╔════════════════════════════╗\n"
        "        👥 REFER & EARN\n"
        "╚════════════════════════════╝\n\n"
        f"💰 Reward: ₹{reward}\n"
        f"👥 Verified: {refs}\n"
        f"🎁 Rewarded: {rewarded}\n\n"
        "🔗 Your Referral Link:\n"
        f"`{link}`",
        parse_mode="Markdown"
    )


# =========================================================
# SUPPORT
# =========================================================

async def support(update, context):

    if not await is_verified(
        update,
        context
    ):
        return

    await update.message.reply_text(
        "╔════════════════════════════╗\n"
        "             🆘 SUPPORT\n"
        "╚════════════════════════════╝\n\n"
        "Payment, wallet ya order issue ke liye "
        "support contact karo.\n\n"
        f"👨‍💻 {SUPPORT_USERNAME}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🆘 CONTACT SUPPORT",
                    url=(
                        "https://t.me/"
                        + SUPPORT_USERNAME.lstrip("@")
                    )
                )
            ]
        ])
    )


# =========================================================
# CHECK UID
# =========================================================

async def check_uid(update, context):

    if not await is_verified(
        update,
        context
    ):
        return

    clear_state(context)

    context.user_data["check_uid"] = True

    await update.message.reply_text(
        "🔍 **CHECK UID**\n\n"
        "Game UID bhejo.",
        parse_mode="Markdown"
    )


def fetch_info(uid):

    try:

        r = requests.get(
            INFO_API,
            params={"uid": uid},
            timeout=20
        )

        r.raise_for_status()

        return r.json()

    except Exception as e:

        return {
            "error": str(e)
        }


def find_value(data, keywords):

    if isinstance(data, dict):

        for key, value in data.items():

            key_lower = str(key).lower()

            if any(
                k in key_lower
                for k in keywords
            ):

                return value

            result = find_value(
                value,
                keywords
            )

            if result is not None:
                return result

    elif isinstance(data, list):

        for item in data:

            result = find_value(
                item,
                keywords
            )

            if result is not None:
                return result

    return None


async def check_uid_handler(update, context):

    uid = update.message.text.strip()

    if not uid.isdigit():

        await update.message.reply_text(
            "❌ UID sirf numbers mein bhejo."
        )

        return

    clear_state(context)

    msg = await update.message.reply_text(
        "⏳ 🔍 UID information fetch ho rahi hai..."
    )

    data = await asyncio.to_thread(
        fetch_info,
        uid
    )

    if data.get("error"):

        await msg.edit_text(
            "❌ UID API error.\n\n"
            + str(data["error"])
        )

        return

    nickname = find_value(
        data,
        ["nickname", "player_name"]
    )

    level = find_value(
        data,
        ["level"]
    )

    likes = find_value(
        data,
        ["liked", "likes", "like_count"]
    )

    region = find_value(
        data,
        ["region", "server"]
    )

    clan = find_value(
        data,
        ["clan_name"]
    )

    # FIX:
    # 0 likes ko N/A nahi dikhayega.
    likes_display = (
        "N/A"
        if likes is None
        else str(likes)
    )

    await msg.edit_text(
        "╔════════════════════════════╗\n"
        "            👤 UID INFO\n"
        "╚════════════════════════════╝\n\n"
        f"🆔 UID: `{uid}`\n"
        f"👤 Name: `{nickname or 'N/A'}`\n"
        f"⭐ Level: `{level or 'N/A'}`\n"
        f"❤️ Likes: `{likes_display}`\n"
        f"🌍 Region: `{region or 'N/A'}`\n"
        f"🏰 Clan: `{clan or 'N/A'}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✅ Information fetched.",
        parse_mode="Markdown"
    )


# =========================================================
# CC STORE
# =========================================================

async def cc_store(update, context):

    if not await is_verified(
        update,
        context
    ):
        return

    name = setting(
        "cc_name",
        "💎 Premium Digital Store"
    )

    price = float(
        setting(
            "cc_price",
            "100"
        )
    )

    value = setting(
        "cc_value",
        "₹3,000"
    )

    desc = setting(
        "cc_description",
        "Premium digital product"
    )

    await update.message.reply_text(
        "╔════════════════════════════╗\n"
        "             🛒 CC STORE\n"
        "╚════════════════════════════╝\n\n"
        f"💎 {name}\n\n"
        f"💰 Price: ₹{price:g}\n"
        f"💵 Value: {value}\n"
        "🆔 UID: Not Required\n"
        "⚡ Delivery: Instant\n"
        f"📦 Stock: {get_cc_stock()}\n\n"
        f"📋 {desc}\n\n"
        "━━━━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"🛒 BUY NOW • ₹{price:g}",
                    callback_data="cc_buy"
                )
            ]
        ])
    )


def get_cc_stock():

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM cc_items
        WHERE sold=0
    """)

    count = cur.fetchone()[0]

    con.close()

    return count


async def cc_buy(update, context):

    q = update.callback_query

    await q.answer()

    user_id = q.from_user.id

    price = float(
        setting(
            "cc_price",
            "100"
        )
    )

    balance = get_balance(user_id)

    if balance < price:

        await q.message.reply_text(
            "❌ **LOW BALANCE**\n\n"
            f"💰 Required: ₹{price:g}\n"
            f"💵 Balance: ₹{balance:.2f}",
            parse_mode="Markdown"
        )

        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT id, item
        FROM cc_items
        WHERE sold=0
        ORDER BY id ASC
        LIMIT 1
    """)

    row = cur.fetchone()

    if not row:

        con.close()

        await q.message.reply_text(
            "⏳ **OUT OF STOCK**\n\n"
            "Admin se new stock add karwao.",
            parse_mode="Markdown"
        )

        return

    item_id, item = row

    # First reserve item atomically
    cur.execute("""
        UPDATE cc_items
        SET sold=1, sold_to=?
        WHERE id=?
        AND sold=0
    """, (
        user_id,
        item_id
    ))

    changed = cur.rowcount

    if changed != 1:

        con.rollback()
        con.close()

        await q.message.reply_text(
            "⚠️ Item already sold. Dobara try karo."
        )

        return

    con.commit()
    con.close()

    # Then charge wallet.
    if not debit(
        user_id,
        price,
        "CC Store Purchase"
    ):

        # Payment failed, restore stock
        con = connect()
        cur = con.cursor()

        cur.execute("""
            UPDATE cc_items
            SET sold=0, sold_to=NULL
            WHERE id=?
        """, (item_id,))

        con.commit()
        con.close()

        await q.message.reply_text(
            "❌ Wallet balance change nahi ho saka."
        )

        return

    order_id = (
        "CC-"
        + uuid.uuid4().hex[:8].upper()
    )

    await q.message.reply_text(
        "╔════════════════════════════╗\n"
        "       ✅ PURCHASE SUCCESS\n"
        "╚════════════════════════════╝\n\n"
        f"🧾 Order: `{order_id}`\n"
        "📦 Product: CC Store\n"
        f"💰 Paid: ₹{price:g}\n"
        "📌 Status: Completed\n\n"
        "🔐 Authorized digital item:\n"
        f"`{item}`\n\n"
        f"💵 Balance: ₹{get_balance(user_id):.2f}",
        parse_mode="Markdown"
    )


# =========================================================
# ADMIN PANEL
# =========================================================

def admin_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📊 Dashboard",
                callback_data="admin_dashboard"
            ),
            InlineKeyboardButton(
                "👥 Users",
                callback_data="admin_users"
            )
        ],
        [
            InlineKeyboardButton(
                "💰 View Wallet",
                callback_data="admin_view_wallet"
            ),
            InlineKeyboardButton(
                "➕ Add Balance",
                callback_data="admin_add_balance"
            )
        ],
        [
            InlineKeyboardButton(
                "➖ Deduct Balance",
                callback_data="admin_deduct"
            ),
            InlineKeyboardButton(
                "🧾 Transactions",
                callback_data="admin_transactions"
            )
        ],
        [
            InlineKeyboardButton(
                "💳 Pending UTR",
                callback_data="admin_utr"
            ),
            InlineKeyboardButton(
                "❤️ Pending Likes",
                callback_data="admin_likes"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 All Orders",
                callback_data="admin_orders"
            ),
            InlineKeyboardButton(
                "👥 Referrals",
                callback_data="admin_referrals"
            )
        ],
        [
            InlineKeyboardButton(
                "🛒 CC Store",
                callback_data="admin_cc"
            ),
            InlineKeyboardButton(
                "📦 CC Stock",
                callback_data="admin_cc_stock"
            )
        ],
        [
            InlineKeyboardButton(
                "💸 Referral Reward",
                callback_data="admin_ref_reward"
            ),
            InlineKeyboardButton(
                "📢 Broadcast",
                callback_data="admin_broadcast"
            )
        ],
        [
            InlineKeyboardButton(
                "❤️ Plan Settings",
                callback_data="admin_plans"
            ),
            InlineKeyboardButton(
                "⚙️ Settings",
                callback_data="admin_settings"
            )
        ],
    ])


async def admin_panel(update, context):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ Admin only."
        )

        return

    clear_state(context)

    await update.message.reply_text(
        "╔════════════════════════════╗\n"
        "          👑 VIP ADMIN PANEL\n"
        "╚════════════════════════════╝\n\n"
        "🛠️ Complete management center\n\n"
        "👇 Option select karo.",
        reply_markup=admin_keyboard()
    )


# =========================================================
# ADMIN CALLBACK
# =========================================================

async def admin_callback(update, context):

    q = update.callback_query

    if q.from_user.id != ADMIN_ID:

        await q.answer(
            "❌ Admin only.",
            show_alert=True
        )

        return

    await q.answer()

    data = q.data

    # Dashboard
    if data == "admin_dashboard":

        con = connect()
        cur = con.cursor()

        cur.execute(
            "SELECT COUNT(*) FROM users"
        )

        users = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM orders"
        )

        orders = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM orders
            WHERE status='Pending Approval'
        """)

        pending_likes = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM deposits
            WHERE status='pending'
        """)

        pending_utr = cur.fetchone()[0]

        cur.execute("""
            SELECT COALESCE(SUM(balance),0)
            FROM users
        """)

        wallet = cur.fetchone()[0]

        con.close()

        await q.message.reply_text(
            "📊 **VIP DASHBOARD**\n\n"
            f"👥 Users: {users}\n"
            f"📦 Orders: {orders}\n"
            f"❤️ Pending Likes: {pending_likes}\n"
            f"💳 Pending UTR: {pending_utr}\n"
            f"💰 Total Wallet: ₹{wallet:.2f}",
            parse_mode="Markdown"
        )

        return

    # View wallet
    if data == "admin_view_wallet":

        clear_state(context)

        context.user_data["admin_wallet"] = True

        await q.message.reply_text(
            "👤 User Telegram ID bhejo."
        )

        return

    # Add balance
    if data == "admin_add_balance":

        clear_state(context)

        context.user_data["admin_add"] = True

        await q.message.reply_text(
            "💰 Format:\n"
            "`USER_ID AMOUNT`\n\n"
            "Example:\n"
            "`123456789 100`",
            parse_mode="Markdown"
        )

        return

    # Deduct
    if data == "admin_deduct":

        clear_state(context)

        context.user_data["admin_deduct"] = True

        await q.message.reply_text(
            "➖ Format:\n"
            "`USER_ID AMOUNT`",
            parse_mode="Markdown"
        )

        return

    # Transactions
    if data == "admin_transactions":

        clear_state(context)

        context.user_data["admin_tx"] = True

        await q.message.reply_text(
            "User ID bhejo."
        )

        return

    # Users
    if data == "admin_users":

        con = connect()
        cur = con.cursor()

        cur.execute("""
            SELECT user_id, username,
                   balance, created
            FROM users
            ORDER BY created DESC
            LIMIT 20
        """)

        rows = cur.fetchall()

        con.close()

        text = "👥 **RECENT USERS**\n\n"

        for uid, username, bal, created in rows:

            text += (
                f"🆔 `{uid}`\n"
                f"👤 @{username or 'N/A'}\n"
                f"💰 ₹{bal:.2f}\n"
                f"🕐 {created}\n"
                "━━━━━━━━━━━━\n"
            )

        await q.message.reply_text(
            text,
            parse_mode="Markdown"
        )

        return

    # Pending UTR
    if data == "admin_utr":

        con = connect()
        cur = con.cursor()

        cur.execute("""
            SELECT deposit_id, user_id,
                   amount, utr, created
            FROM deposits
            WHERE status='pending'
            ORDER BY created
            LIMIT 20
        """)

        rows = cur.fetchall()

        con.close()

        if not rows:

            await q.message.reply_text(
                "✅ No pending UTR."
            )

            return

        for deposit_id, uid, amount, utr, created in rows:

            await q.message.reply_text(
                "💳 **PENDING UTR**\n\n"
                f"🧾 `{deposit_id}`\n"
                f"👤 `{uid}`\n"
                f"💰 ₹{amount:.2f}\n"
                f"🔢 `{utr}`\n"
                f"🕐 {created}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "✅ APPROVE",
                            callback_data=f"depositapprove:{deposit_id}"
                        ),
                        InlineKeyboardButton(
                            "❌ REJECT",
                            callback_data=f"depositreject:{deposit_id}"
                        )
                    ]
                ])
            )

        return

    # Pending Likes
    if data == "admin_likes":

        con = connect()
        cur = con.cursor()

        cur.execute("""
            SELECT order_id, user_id,
                   uid, plan_id, amount
            FROM orders
            WHERE status='Pending Approval'
            ORDER BY created
            LIMIT 20
        """)

        rows = cur.fetchall()

        con.close()

        if not rows:

            await q.message.reply_text(
                "✅ No pending Like plans."
            )

            return

        for (
            order_id,
            uid_user,
            game_uid,
            plan_id,
            amount
        ) in rows:

            await q.message.reply_text(
                "❤️ **PENDING LIKE PLAN**\n\n"
                f"🧾 `{order_id}`\n"
                f"👤 `{uid_user}`\n"
                f"🆔 `{game_uid}`\n"
                f"📦 {get_plan_name(plan_id)}\n"
                f"💰 ₹{amount:g}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "✅ APPROVE",
                            callback_data=f"likeapprove:{order_id}"
                        ),
                        InlineKeyboardButton(
                            "❌ REJECT",
                            callback_data=f"likereject:{order_id}"
                        )
                    ]
                ])
            )

        return

    # Orders
    if data == "admin_orders":

        con = connect()
        cur = con.cursor()

        cur.execute("""
            SELECT order_id, user_id,
                   uid, plan_id,
                   amount, status,
                   expiry_time
            FROM orders
            ORDER BY created DESC
            LIMIT 20
        """)

        rows = cur.fetchall()

        con.close()

        if not rows:

            await q.message.reply_text(
                "📦 No orders."
            )

            return

        text = "📦 **RECENT ORDERS**\n\n"

        for (
            order_id,
            uid_user,
            game_uid,
            plan_id,
            amount,
            status,
            expiry
        ) in rows:

            text += (
                f"🧾 `{order_id}`\n"
                f"👤 `{uid_user}`\n"
                f"🆔 `{game_uid}`\n"
                f"📦 {get_plan_name(plan_id)}\n"
                f"💰 ₹{amount:g}\n"
                f"📌 {status}\n"
            )

            if expiry:
                text += (
                    f"🔴 {expiry}\n"
                )

            text += "━━━━━━━━━━━━\n"

        await q.message.reply_text(
            text,
            parse_mode="Markdown"
        )

        return

    # Referral stats
    if data == "admin_referrals":

        con = connect()
        cur = con.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE referred_by IS NOT NULL
        """)

        total = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE referral_rewarded=1
        """)

        rewarded = cur.fetchone()[0]

        con.close()

        await q.message.reply_text(
            "👥 **REFERRAL STATS**\n\n"
            f"👥 Total: {total}\n"
            f"🎁 Rewarded: {rewarded}\n"
            f"💰 Current Reward: ₹{setting('referral_reward','2')}",
            parse_mode="Markdown"
        )

        return

    # Referral reward
    if data == "admin_ref_reward":

        clear_state(context)

        context.user_data["admin_ref_reward"] = True

        await q.message.reply_text(
            "💸 New referral reward amount bhejo.\n"
            "Example: `5`"
        )

        return

    # Broadcast
    if data == "admin_broadcast":

        clear_state(context)

        context.user_data["admin_broadcast"] = True

        await q.message.reply_text(
            "📢 Broadcast message bhejo.\n\n"
            "Text/photo/video bhej sakte ho.\n"
            "/cancel se cancel."
        )

        return

    # CC settings
    if data == "admin_cc":

        await q.message.reply_text(
            "🛒 **CC STORE SETTINGS**\n\n"
            f"💎 Name: {setting('cc_name')}\n"
            f"💰 Price: ₹{setting('cc_price')}\n"
            f"💵 Value: {setting('cc_value')}\n"
            f"📦 Stock: {get_cc_stock()}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✏️ Name",
                        callback_data="cc_edit_name"
                    ),
                    InlineKeyboardButton(
                        "💰 Price",
                        callback_data="cc_edit_price"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "💵 Value",
                        callback_data="cc_edit_value"
                    ),
                    InlineKeyboardButton(
                        "📋 Description",
                        callback_data="cc_edit_desc"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "➕ Add Stock",
                        callback_data="cc_add_stock"
                    )
                ]
            ])
        )

        return

    # CC stock
    if data == "admin_cc_stock":

        con = connect()
        cur = con.cursor()

        cur.execute("""
            SELECT id, item
            FROM cc_items
            WHERE sold=0
            ORDER BY id DESC
            LIMIT 20
        """)

        rows = cur.fetchall()

        con.close()

        text = (
            "📦 **CC STOCK**\n\n"
            f"Available: {len(rows)}\n\n"
        )

        for item_id, item in rows:

            text += (
                f"#{item_id} • `{item}`\n"
            )

        await q.message.reply_text(
            text,
            parse_mode="Markdown"
        )

        return

    # Plans
    if data == "admin_plans":

        con = connect()
        cur = con.cursor()

        cur.execute("""
            SELECT plan_id, name,
                   days, daily, price,
                   active
            FROM plans
            ORDER BY price
        """)

        rows = cur.fetchall()

        con.close()

        text = "❤️ **LIKE PLANS**\n\n"

        for (
            pid,
            name,
            days,
            daily,
            price,
            active
        ) in rows:

            text += (
                f"💎 {name}\n"
                f"ID: `{pid}`\n"
                f"❤️ {daily}/day\n"
                f"📅 {days} day(s)\n"
                f"💰 ₹{price:g}\n"
                f"📌 {'ON' if active else 'OFF'}\n"
                "━━━━━━━━━━━━\n"
            )

        await q.message.reply_text(
            text,
            parse_mode="Markdown"
        )

        return

    # Settings
    if data == "admin_settings":

        await q.message.reply_text(
            "⚙️ **BOT SETTINGS**\n\n"
            f"🆔 Admin: `{ADMIN_ID}`\n"
            f"💳 UPI: `{UPI_ID}`\n"
            f"🎁 Referral: ₹{setting('referral_reward','2')}\n"
            f"📢 Channels: {len(REQUIRED_CHANNELS)}",
            parse_mode="Markdown"
        )

        return

    # CC edits
    cc_states = {
        "cc_edit_name": "cc_name",
        "cc_edit_price": "cc_price",
        "cc_edit_value": "cc_value",
        "cc_edit_desc": "cc_description",
        "cc_add_stock": "cc_stock",
    }

    if data in cc_states:

        clear_state(context)

        state = cc_states[data]

        context.user_data[state] = True

        prompts = {
            "cc_name":
                "💎 New CC Store name bhejo.",
            "cc_price":
                "💰 New price bhejo.",
            "cc_value":
                "💵 New value bhejo.",
            "cc_description":
                "📋 New description bhejo.",
            "cc_stock":
                "➕ Authorized digital item/code bhejo."
        }

        await q.message.reply_text(
            prompts[state]
        )

        return


# =========================================================
# ADMIN TEXT
# =========================================================

async def admin_text(update, context):

    text = update.message.text.strip()

    # View wallet
    if context.user_data.get("admin_wallet"):

        clear_state(context)

        if not text.isdigit():

            await update.message.reply_text(
                "❌ Numeric User ID required."
            )

            return

        uid = int(text)

        con = connect()
        cur = con.cursor()

        cur.execute("""
            SELECT username, balance, created
            FROM users
            WHERE user_id=?
        """, (uid,))

        row = cur.fetchone()

        con.close()

        if not row:

            await update.message.reply_text(
                "❌ User not found."
            )

            return

        username, bal, created = row

        await update.message.reply_text(
            "👤 **USER WALLET**\n\n"
            f"🆔 `{uid}`\n"
            f"👤 @{username or 'N/A'}\n"
            f"💰 ₹{bal:.2f}\n"
            f"🕐 {created}",
            parse_mode="Markdown"
        )

        return

    # Add balance
    if context.user_data.get("admin_add"):

        clear_state(context)

        parts = text.split()

        if len(parts) != 2:

            await update.message.reply_text(
                "`USER_ID AMOUNT`",
                parse_mode="Markdown"
            )

            return

        try:

            uid = int(parts[0])
            amount = float(parts[1])

        except ValueError:

            await update.message.reply_text(
                "❌ Invalid."
            )

            return

        if amount <= 0:

            await update.message.reply_text(
                "❌ Amount must be greater than 0."
            )

            return

        con = connect()
        cur = con.cursor()

        cur.execute(
            "SELECT user_id FROM users WHERE user_id=?",
            (uid,)
        )

        exists = cur.fetchone()

        con.close()

        if not exists:

            await update.message.reply_text(
                "❌ User not found."
            )

            return

        credit(
            uid,
            amount,
            "Admin wallet credit"
        )

        new_bal = get_balance(uid)

        await update.message.reply_text(
            "✅ **BALANCE ADDED**\n\n"
            f"👤 `{uid}`\n"
            f"➕ ₹{amount:.2f}\n"
            f"💰 ₹{new_bal:.2f}",
            parse_mode="Markdown"
        )

        try:

            await context.bot.send_message(
                uid,
                "💰 **WALLET CREDITED**\n\n"
                f"➕ ₹{amount:.2f}\n"
                f"💵 Balance: ₹{new_bal:.2f}",
                parse_mode="Markdown"
            )

        except Exception:
            pass

        return

    # Deduct
    if context.user_data.get("admin_deduct"):

        clear_state(context)

        parts = text.split()

        if len(parts) != 2:

            await update.message.reply_text(
                "`USER_ID AMOUNT`",
                parse_mode="Markdown"
            )

            return

        try:

            uid = int(parts[0])
            amount = float(parts[1])

        except ValueError:

            await update.message.reply_text(
                "❌ Invalid."
            )

            return

        if amount <= 0:

            await update.message.reply_text(
                "❌ Amount must be greater than 0."
            )

            return

        if get_balance(uid) < amount:

            await update.message.reply_text(
                "❌ User balance insufficient."
            )

            return

        if not debit(
            uid,
            amount,
            "Admin wallet deduction"
        ):

            await update.message.reply_text(
                "❌ Deduction failed."
            )

            return

        await update.message.reply_text(
            "✅ Deducted.\n\n"
            f"👤 `{uid}`\n"
            f"➖ ₹{amount:.2f}\n"
            f"💰 ₹{get_balance(uid):.2f}",
            parse_mode="Markdown"
        )

        return

    # Transactions
    if context.user_data.get("admin_tx"):

        clear_state(context)

        if not text.isdigit():
            return

        uid = int(text)

        con = connect()
        cur = con.cursor()

        cur.execute("""
            SELECT amount, note, created
            FROM transactions
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT 20
        """, (uid,))

        rows = cur.fetchall()

        con.close()

        if not rows:

            await update.message.reply_text(
                "🧾 No transactions."
            )

            return

        result = (
            f"🧾 **USER TRANSACTIONS**\n\n"
        )

        for amount, note, created in rows:

            result += (
                f"{'➕' if amount >= 0 else '➖'} "
                f"₹{abs(amount):.2f}\n"
                f"📌 {note}\n"
                f"🕐 {created}\n"
                "━━━━━━━━━━━━\n"
            )

        await update.message.reply_text(
            result,
            parse_mode="Markdown"
        )

        return

    # Referral reward
    if context.user_data.get(
        "admin_ref_reward"
    ):

        clear_state(context)

        try:

            reward = float(text)

        except ValueError:

            await update.message.reply_text(
                "❌ Invalid amount."
            )

            return

        if reward < 0:

            await update.message.reply_text(
                "❌ Reward cannot be negative."
            )

            return

        set_setting(
            "referral_reward",
            reward
        )

        await update.message.reply_text(
            f"✅ Referral reward updated to ₹{reward:g}"
        )

        return

    # Broadcast
    if context.user_data.get(
        "admin_broadcast"
    ):

        clear_state(context)

        con = connect()
        cur = con.cursor()

        cur.execute(
            "SELECT user_id FROM users"
        )

        users = [
            x[0]
            for x in cur.fetchall()
        ]

        con.close()

        sent = 0
        failed = 0

        await update.message.reply_text(
            f"📢 Broadcast starting...\n"
            f"👥 Users: {len(users)}"
        )

        for uid in users:

            try:

                await update.message.copy(
                    chat_id=uid
                )

                sent += 1

                await asyncio.sleep(
                    0.05
                )

            except (
                Forbidden,
                BadRequest
            ):

                failed += 1

            except Exception:

                failed += 1

        await update.message.reply_text(
            "📢 **BROADCAST COMPLETE**\n\n"
            f"✅ Sent: {sent}\n"
            f"❌ Failed: {failed}",
            parse_mode="Markdown"
        )

        return

    # CC name
    if context.user_data.get("cc_name"):

        clear_state(context)

        set_setting(
            "cc_name",
            text
        )

        await update.message.reply_text(
            "✅ CC Store name updated."
        )

        return

    # CC price
    if context.user_data.get("cc_price"):

        clear_state(context)

        try:

            price = float(text)

        except ValueError:

            await update.message.reply_text(
                "❌ Invalid price."
            )

            return

        if price <= 0:

            await update.message.reply_text(
                "❌ Price must be greater than 0."
            )

            return

        set_setting(
            "cc_price",
            price
        )

        await update.message.reply_text(
            f"✅ CC price: ₹{price:g}"
        )

        return

    # CC value
    if context.user_data.get("cc_value"):

        clear_state(context)

        set_setting(
            "cc_value",
            text
        )

        await update.message.reply_text(
            "✅ CC value updated."
        )

        return

    # CC description
    if context.user_data.get(
        "cc_description"
    ):

        clear_state(context)

        set_setting(
            "cc_description",
            text
        )

        await update.message.reply_text(
            "✅ CC description updated."
        )

        return

    # CC stock
    if context.user_data.get("cc_stock"):

        clear_state(context)

        con = connect()
        cur = con.cursor()

        cur.execute("""
            INSERT OR IGNORE INTO cc_items(item)
            VALUES(?)
        """, (text,))

        con.commit()
        con.close()

        await update.message.reply_text(
            "✅ Authorized digital stock added.\n"
            f"📦 Stock: {get_cc_stock()}"
        )

        return


# =========================================================
# GENERAL TEXT ROUTER
# =========================================================

async def text_router(update, context):

    user = update.effective_user

    create_user(
        user.id,
        user.username or ""
    )

    # Admin states
    if user.id == ADMIN_ID:

        admin_states = [
            "admin_wallet",
            "admin_add",
            "admin_deduct",
            "admin_tx",
            "admin_ref_reward",
            "admin_broadcast",
            "cc_name",
            "cc_price",
            "cc_value",
            "cc_description",
            "cc_stock",
        ]

        if any(
            context.user_data.get(x)
            for x in admin_states
        ):

            await admin_text(
                update,
                context
            )

            return

    # Like UID
    if context.user_data.get(
        "waiting_like_uid"
    ):

        if not await is_verified(
            update,
            context
        ):
            return

        await like_uid_handler(
            update,
            context
        )

        return

    # Deposit amount
    if context.user_data.get(
        "deposit_amount"
    ):

        if not await is_verified(
            update,
            context
        ):
            return

        await deposit_amount_handler(
            update,
            context
        )

        return

    # UTR
    if context.user_data.get(
        "waiting_utr"
    ):

        if not await is_verified(
            update,
            context
        ):
            return

        await utr_handler(
            update,
            context
        )

        return

    # Check UID
    if context.user_data.get(
        "check_uid"
    ):

        if not await is_verified(
            update,
            context
        ):
            return

        await check_uid_handler(
            update,
            context
        )

        return

    text = update.message.text

    if text == "❤️ Buy Like":

        await buy_like(
            update,
            context
        )

    elif text == "🛒 CC Store":

        await cc_store(
            update,
            context
        )

    elif text == "🔍 Check UID":

        await check_uid(
            update,
            context
        )

    elif text == "💰 Wallet":

        await wallet(
            update,
            context
        )

    elif text == "👥 Refer & Earn":

        await referral(
            update,
            context
        )

    elif text == "➕ Add Money":

        await add_money(
            update,
            context
        )

    elif text == "📦 My Orders":

        await my_orders(
            update,
            context
        )

    elif text == "🆘 Support":

        await support(
            update,
            context
        )

    else:

        if not await is_verified(
            update,
            context
        ):
            return

        await update.message.reply_text(
            "👑 Menu se option select karo.",
            reply_markup=main_keyboard()
        )


# =========================================================
# CALLBACK ROUTER
# =========================================================

async def callback_router(update, context):

    data = update.callback_query.data

    if data == "check_join":

        q = update.callback_query

        await q.answer()

        if await is_verified(
            update,
            context
        ):

            await q.message.reply_text(
                "╔════════════════════════════╗\n"
                "       ✅ ACCESS VERIFIED\n"
                "╚════════════════════════════╝\n\n"
                "🎉 VIP access unlocked.",
                reply_markup=main_keyboard()
            )

        return

    if data.startswith("likeplan:"):

        if not await is_verified(
            update,
            context
        ):
            return

        await like_plan_callback(
            update,
            context
        )

        return

    if (
        data.startswith("likeapprove:")
        or data.startswith("likereject:")
    ):

        await like_approval(
            update,
            context
        )

        return

    if (
        data.startswith("depositapprove:")
        or data.startswith("depositreject:")
    ):

        await deposit_action(
            update,
            context
        )

        return

    if data == "cc_buy":

        if not await is_verified(
            update,
            context
        ):
            return

        await cc_buy(
            update,
            context
        )

        return

    if data.startswith("wallet_"):

        if not await is_verified(
            update,
            context
        ):
            return

        await wallet_callback(
            update,
            context
        )

        return

    if (
        data.startswith("admin_")
        or data.startswith("cc_")
    ):

        await admin_callback(
            update,
            context
        )

        return


# =========================================================
# CANCEL
# =========================================================

async def cancel(update, context):

    clear_state(context)

    await update.message.reply_text(
        "❌ Current action cancelled.",
        reply_markup=main_keyboard()
    )


# =========================================================
# EXTRA API COMMANDS
# =========================================================

async def acc(update, context):

    if not await is_verified(
        update,
        context
    ):
        return

    if not context.args:

        await update.message.reply_text(
            "/acc UID"
        )

        return

    uid = context.args[0]

    data = await asyncio.to_thread(
        fetch_info,
        uid
    )

    nickname = find_value(
        data,
        ["nickname"]
    )

    likes = find_value(
        data,
        ["liked", "likes"]
    )

    likes_display = (
        "N/A"
        if likes is None
        else str(likes)
    )

    await update.message.reply_text(
        f"👤 Name: `{nickname or 'N/A'}`\n"
        f"❤️ Likes: `{likes_display}`",
        parse_mode="Markdown"
    )


async def ban(update, context):

    if not await is_verified(
        update,
        context
    ):
        return

    if not context.args:

        await update.message.reply_text(
            "/ban UID"
        )

        return

    uid = context.args[0]

    try:

        r = await asyncio.to_thread(
            requests.get,
            BAN_API,
            params={"uid": uid},
            timeout=20
        )

        await update.message.reply_text(
            r.text[:4000]
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ API Error: {e}"
        )


async def icon(update, context):

    if not await is_verified(
        update,
        context
    ):
        return

    if not context.args:

        await update.message.reply_text(
            "/icon ICON_ID"
        )

        return

    icon_id = context.args[0]

    await update.message.reply_photo(
        photo=f"{ICON_API}?icon_id={icon_id}"
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(update, context):

    error = context.error

    if isinstance(error, Forbidden):

        print(
            "Telegram Forbidden: user blocked the bot "
            "or chat is unavailable."
        )

        return

    if isinstance(error, BadRequest):

        print(
            "Telegram BadRequest:",
            error
        )

        return

    print(
        "Unhandled error:",
        repr(error)
    )


# =========================================================
# MAIN
# =========================================================

def main():

    init_db()

    if not BOT_TOKEN:

        print(
            "❌ BOT_TOKEN environment variable set karo."
        )

        return

    # Render Web Service ko port chahiye
    threading.Thread(
        target=run_web,
        daemon=True
    ).start()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_error_handler(
        error_handler
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin_panel
        )
    )

    app.add_handler(
        CommandHandler(
            "cancel",
            cancel
        )
    )

    app.add_handler(
        CommandHandler(
            "acc",
            acc
        )
    )

    app.add_handler(
        CommandHandler(
            "ban",
            ban
        )
    )

    app.add_handler(
        CommandHandler(
            "icon",
            icon
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )

    print(
        "===================================="
    )

    print(
        "        👑 VIP BOT STARTED"
    )

    print(
        "        🌐 WEB SERVER STARTED"
    )

    print(
        "===================================="
    )

    app.run_polling()


if __name__ == "__main__":
    main()
