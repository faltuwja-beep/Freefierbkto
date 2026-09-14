import os
import sqlite3
import uuid
import threading
from datetime import datetime, timedelta, timezone

from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
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

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable set karo.")

ADMIN_ID = int(os.getenv("ADMIN_ID", "7161571409"))
UPI_ID = os.getenv("UPI_ID", "sima6241@ptaxis")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@your_support")
DB_FILE = os.getenv("DB_FILE", "vipbot.db")

REQUIRED_CHANNELS = [
    ("Bot Like Proof", "@botlikeproof", "https://t.me/botlikeproof"),
    ("Earning With Ask 9", "@eraningwithask9", "https://t.me/eraningwithask9"),
    ("Earning With Ask", "@eraningwithask", "https://t.me/eraningwithask"),
]

# =========================================================
# RENDER WEB SERVER
# =========================================================

web_app = Flask(__name__)

@web_app.get("/")
def home():
    return "VIP Bot is running", 200

@web_app.get("/health")
def health():
    return "OK", 200

def run_web():
    port = int(os.getenv("PORT", "10000"))
    web_app.run(host="0.0.0.0", port=port, use_reloader=False)

# =========================================================
# DATABASE
# =========================================================

def connect():
    con = sqlite3.connect(DB_FILE, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=30000")
    return con

def init_db():
    con = connect()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance REAL NOT NULL DEFAULT 0,
        referred_by INTEGER,
        referral_paid INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        daily_likes INTEGER NOT NULL DEFAULT 1,
        days INTEGER NOT NULL,
        price REAL NOT NULL,
        active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        plan_code TEXT NOT NULL,
        uid TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        approved_at TEXT,
        expires_at TEXT,
        note TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS deposits (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        utr TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        reviewed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        kind TEXT NOT NULL,
        amount REAL NOT NULL,
        balance_after REAL NOT NULL,
        reference TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER NOT NULL,
        referred_id INTEGER NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'pending',
        reward REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        paid_at TEXT
    );

    CREATE TABLE IF NOT EXISTS cc_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        value_text TEXT NOT NULL,
        description TEXT NOT NULL,
        stock INTEGER NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS cc_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        code TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'available',
        sold_to INTEGER,
        sold_at TEXT
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    defaults = [
        ("referral_reward", "2"),
        ("cc_name", "Digital Code"),
        ("cc_price", "100"),
        ("cc_value", "₹3,000 value"),
        ("cc_description", "Authorized digital item/code. Delivery is automatic from available stock."),
    ]
    for key, value in defaults:
        con.execute(
            "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
            (key, value),
        )

    plans = [
        ("demo", "🎁 Demo", 1, 1, 5),
        ("starter", "🚀 Starter", 220, 15, 59),
        ("pro", "💎 Pro", 220, 30, 99),
    ]
    for code, name, daily, days, price in plans:
        con.execute(
            """INSERT OR IGNORE INTO plans
               (code,name,daily_likes,days,price,active)
               VALUES(?,?,?,?,?,1)""",
            (code, name, daily, days, price),
        )

    con.commit()
    con.close()

def now():
    return datetime.now(timezone.utc)

def now_text():
    return now().isoformat()

def fmt_date(value):
    if not value:
        return "-"
    try:
        dt = datetime.fromisoformat(value)
        return dt.astimezone().strftime("%d-%m-%Y %I:%M %p")
    except Exception:
        return value

def get_setting(key, default=""):
    con = connect()
    row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    con.close()
    return row["value"] if row else default

def set_setting(key, value):
    con = connect()
    con.execute(
        """INSERT INTO settings(key,value) VALUES(?,?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
        (key, str(value)),
    )
    con.commit()
    con.close()

def ensure_user(tg_user, referred_by=None):
    con = connect()
    row = con.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (tg_user.id,),
    ).fetchone()

    if row:
        con.execute(
            "UPDATE users SET username=?, first_name=? WHERE user_id=?",
            (tg_user.username or "", tg_user.first_name or "", tg_user.id),
        )
    else:
        valid_ref = None
        if referred_by and referred_by != tg_user.id:
            ref_exists = con.execute(
                "SELECT user_id FROM users WHERE user_id=?",
                (referred_by,),
            ).fetchone()
            if ref_exists:
                valid_ref = referred_by

        con.execute(
            """INSERT INTO users
               (user_id,username,first_name,referred_by,created_at)
               VALUES(?,?,?,?,?)""",
            (
                tg_user.id,
                tg_user.username or "",
                tg_user.first_name or "",
                valid_ref,
                now_text(),
            ),
        )
        if valid_ref:
            con.execute(
                """INSERT OR IGNORE INTO referrals
                   (referrer_id,referred_id,status,reward,created_at)
                   VALUES(?,?,?,?,?)""",
                (valid_ref, tg_user.id, "pending", 0, now_text()),
            )

    con.commit()
    con.close()

def balance(user_id):
    con = connect()
    row = con.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,),
    ).fetchone()
    con.close()
    return float(row["balance"]) if row else 0.0

def change_balance(user_id, amount, kind, reference=""):
    con = connect()
    con.execute("BEGIN IMMEDIATE")
    row = con.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,),
    ).fetchone()
    if not row:
        con.rollback()
        con.close()
        return False, 0.0

    old = float(row["balance"])
    new = old + float(amount)
    if new < -0.00001:
        con.rollback()
        con.close()
        return False, old

    con.execute(
        "UPDATE users SET balance=? WHERE user_id=?",
        (new, user_id),
    )
    con.execute(
        """INSERT INTO transactions
           (user_id,kind,amount,balance_after,reference,created_at)
           VALUES(?,?,?,?,?,?)""",
        (user_id, kind, amount, new, reference, now_text()),
    )
    con.commit()
    con.close()
    return True, new

# =========================================================
# UI
# =========================================================

def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["💰 Wallet", "🛒 Buy Like"],
            ["📦 My Orders", "🎁 Referral"],
            ["🏪 CC Store", "🆔 Check UID"],
            ["🛟 Support"],
        ],
        resize_keyboard=True,
    )

def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Dashboard", callback_data="adm_dashboard"),
            InlineKeyboardButton("👥 Users", callback_data="adm_users"),
        ],
        [
            InlineKeyboardButton("💰 Wallet", callback_data="adm_wallet"),
            InlineKeyboardButton("➕ Add Balance", callback_data="adm_add"),
        ],
        [
            InlineKeyboardButton("➖ Deduct", callback_data="adm_deduct"),
            InlineKeyboardButton("📒 Transactions", callback_data="adm_tx"),
        ],
        [
            InlineKeyboardButton("💳 Pending UTR", callback_data="adm_utr"),
            InlineKeyboardButton("❤️ Pending Likes", callback_data="adm_likes"),
        ],
        [
            InlineKeyboardButton("📦 All Orders", callback_data="adm_orders"),
            InlineKeyboardButton("🎁 Referrals", callback_data="adm_refs"),
        ],
        [
            InlineKeyboardButton("🏪 CC Store", callback_data="adm_cc"),
            InlineKeyboardButton("📦 CC Stock", callback_data="adm_stock"),
        ],
        [
            InlineKeyboardButton("💸 Referral Reward", callback_data="adm_reward"),
            InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast"),
        ],
    ])

def clear_state(context):
    context.user_data.clear()

# =========================================================
# CHANNEL CHECK
# =========================================================

async def channels_joined(context, user_id):
    for _, chat, _ in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat, user_id)
            if member.status in ("left", "kicked"):
                return False
        except Exception:
            # If the bot cannot check a channel, don't falsely block the user.
            continue
    return True

async def join_required(update, context):
    buttons = [
        [InlineKeyboardButton(name, url=url)]
        for name, _, url in REQUIRED_CHANNELS
    ]
    buttons.append([InlineKeyboardButton("✅ Check Join", callback_data="check_join")])
    await update.effective_message.reply_text(
        "📢 Pehle required channels join karo, phir Check Join dabao.",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# =========================================================
# START / MENU
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref = None

    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            try:
                ref = int(arg[4:])
            except ValueError:
                ref = None

    ensure_user(user, ref)
    clear_state(context)

    if not await channels_joined(context, user.id):
        await join_required(update, context)
        return

    await update.message.reply_text(
        f"👋 Welcome {user.first_name or 'User'}!\n\n"
        f"💰 Wallet: ₹{balance(user.id):.2f}\n\n"
        "Menu se option choose karo.",
        reply_markup=main_keyboard(),
    )

async def check_join(update, context):
    q = update.callback_query
    await q.answer()

    if await channels_joined(context, q.from_user.id):
        await q.message.reply_text(
            "✅ Channel verification complete.\n\nMenu open hai.",
            reply_markup=main_keyboard(),
        )
    else:
        await q.message.reply_text("❌ Abhi required channels join nahi hue.")

# =========================================================
# WALLET / DEPOSIT
# =========================================================

async def wallet(update, context):
    clear_state(context)
    uid = update.effective_user.id
    await update.message.reply_text(
        f"💰 WALLET\n\n"
        f"Balance: ₹{balance(uid):.2f}\n\n"
        "Neeche option choose karo:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Money", callback_data="wallet_add")],
            [InlineKeyboardButton("📒 Transactions", callback_data="wallet_tx")],
        ]),
    )

async def wallet_callback(update, context):
    q = update.callback_query
    await q.answer()

    if q.data == "wallet_add":
        clear_state(context)
        context.user_data["state"] = "deposit_amount"
        await q.message.reply_text(
            "➕ ADD MONEY\n\n"
            f"UPI ID: `{UPI_ID}`\n\n"
            "Kitna amount add karna hai? Sirf number bhejo.\n"
            "Example: 100",
            parse_mode="Markdown",
        )

    elif q.data == "wallet_tx":
        con = connect()
        rows = con.execute(
            """SELECT kind,amount,balance_after,reference,created_at
               FROM transactions WHERE user_id=?
               ORDER BY id DESC LIMIT 10""",
            (q.from_user.id,),
        ).fetchall()
        con.close()

        if not rows:
            text = "📒 Abhi koi transaction nahi hai."
        else:
            lines = ["📒 LAST TRANSACTIONS\n"]
            for r in rows:
                sign = "+" if r["amount"] >= 0 else ""
                lines.append(
                    f"• {r['kind']}: {sign}₹{r['amount']:.2f}\n"
                    f"  Balance: ₹{r['balance_after']:.2f}\n"
                    f"  {fmt_date(r['created_at'])}"
                )
            text = "\n".join(lines)

        await q.message.reply_text(text)

async def handle_deposit_amount(update, context):
    text = update.message.text.strip()
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("❌ Valid amount bhejo. Example: 100")
        return

    if amount < 1 or amount > 100000:
        await update.message.reply_text("❌ Amount ₹1 se ₹100000 ke beech hona chahiye.")
        return

    context.user_data["deposit_amount_value"] = amount
    context.user_data["state"] = "deposit_utr"

    await update.message.reply_text(
        f"💳 Payment amount: ₹{amount:.2f}\n\n"
        f"UPI ID: `{UPI_ID}`\n\n"
        "Payment complete karke UTR/Transaction ID bhejo.\n"
        "Sirf UTR bhejo.",
        parse_mode="Markdown",
    )

async def handle_deposit_utr(update, context):
    utr = update.message.text.strip()

    if len(utr) < 4 or len(utr) > 100:
        await update.message.reply_text("❌ Valid UTR/Transaction ID bhejo.")
        return

    amount = float(context.user_data.get("deposit_amount_value", 0))
    if amount <= 0:
        clear_state(context)
        await update.message.reply_text("Session expired. Dobara Add Money karo.")
        return

    dep_id = uuid.uuid4().hex[:12]

    con = connect()
    con.execute(
        """INSERT INTO deposits
           (id,user_id,amount,utr,status,created_at)
           VALUES(?,?,?,?,?,?)""",
        (dep_id, update.effective_user.id, amount, utr, "Pending", now_text()),
    )
    con.commit()
    con.close()

    clear_state(context)

    await update.message.reply_text(
        "✅ UTR submit ho gaya.\n\n"
        f"Amount: ₹{amount:.2f}\n"
        f"UTR: {utr}\n"
        "Admin verification ke baad wallet credit hoga.",
        reply_markup=main_keyboard(),
    )

    await context.bot.send_message(
        ADMIN_ID,
        "💳 NEW UTR\n\n"
        f"Deposit ID: `{dep_id}`\n"
        f"User ID: `{update.effective_user.id}`\n"
        f"Username: @{update.effective_user.username or 'none'}\n"
        f"Amount: ₹{amount:.2f}\n"
        f"UTR: `{utr}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"dep_ok:{dep_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"dep_no:{dep_id}"),
            ]
        ]),
    )

# =========================================================
# LIKE ORDERS - MANUAL APPROVAL / PROCESSING
# =========================================================

async def buy_like(update, context):
    clear_state(context)

    if not await channels_joined(context, update.effective_user.id):
        await join_required(update, context)
        return

    con = connect()
    rows = con.execute(
        "SELECT * FROM plans WHERE active=1 ORDER BY price ASC"
    ).fetchall()
    con.close()

    buttons = []
    for p in rows:
        buttons.append([
            InlineKeyboardButton(
                f"{p['name']} • ₹{p['price']}",
                callback_data=f"plan:{p['code']}",
            )
        ])

    await update.message.reply_text(
        "🛒 BUY LIKE\n\nPlan select karo.\n"
        "Orders admin approval ke baad process honge.",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def plan_callback(update, context):
    q = update.callback_query
    await q.answer()

    code = q.data.split(":", 1)[1]
    con = connect()
    p = con.execute(
        "SELECT * FROM plans WHERE code=? AND active=1",
        (code,),
    ).fetchone()
    con.close()

    if not p:
        await q.message.reply_text("❌ Plan unavailable.")
        return

    # Demo: one successful/pending order in the last 24 hours.
    if code == "demo":
        con = connect()
        since = (now() - timedelta(hours=24)).isoformat()
        row = con.execute(
            """SELECT id FROM orders
               WHERE user_id=? AND plan_code='demo'
               AND created_at>=?
               AND status NOT IN ('Rejected','Cancelled')""",
            (q.from_user.id, since),
        ).fetchone()
        con.close()
        if row:
            await q.message.reply_text("⏳ Demo already used/requested in the last 24 hours.")
            return

    if balance(q.from_user.id) < float(p["price"]):
        await q.message.reply_text(
            f"❌ Wallet balance low.\n\n"
            f"Required: ₹{p['price']:.2f}\n"
            f"Balance: ₹{balance(q.from_user.id):.2f}\n\n"
            "Wallet → Add Money karo."
        )
        return

    context.user_data["state"] = "like_uid"
    context.user_data["plan_code"] = code

    await q.message.reply_text(
        f"{p['name']}\n\n"
        f"Daily: {p['daily_likes']}\n"
        f"Duration: {p['days']} day(s)\n"
        f"Price: ₹{p['price']:.2f}\n\n"
        "Free Fire UID bhejo:"
    )

async def handle_like_uid(update, context):
    uid = update.message.text.strip()

    if not uid.isdigit() or not (5 <= len(uid) <= 15):
        await update.message.reply_text("❌ Valid numeric UID bhejo.")
        return

    code = context.user_data.get("plan_code")
    if not code:
        clear_state(context)
        await update.message.reply_text("Session expired. Buy Like dobara karo.")
        return

    con = connect()
    p = con.execute(
        "SELECT * FROM plans WHERE code=? AND active=1",
        (code,),
    ).fetchone()
    con.close()

    if not p:
        clear_state(context)
        await update.message.reply_text("❌ Plan unavailable.")
        return

    # Reserve the money immediately to prevent spending it twice.
    ok, new_balance = change_balance(
        update.effective_user.id,
        -float(p["price"]),
        "Like order reserve",
        "pending-order",
    )
    if not ok:
        clear_state(context)
        await update.message.reply_text("❌ Wallet balance insufficient.")
        return

    order_id = "ORD-" + uuid.uuid4().hex[:10].upper()

    con = connect()
    con.execute(
        """INSERT INTO orders
           (id,user_id,plan_code,uid,amount,status,created_at,note)
           VALUES(?,?,?,?,?,?,?,?)""",
        (
            order_id,
            update.effective_user.id,
            code,
            uid,
            float(p["price"]),
            "Pending Approval",
            now_text(),
            "",
        ),
    )
    con.commit()
    con.close()

    clear_state(context)

    await update.message.reply_text(
        "✅ Order submitted.\n\n"
        f"Order: `{order_id}`\n"
        f"UID: `{uid}`\n"
        f"Amount: ₹{p['price']:.2f}\n"
        "Status: Pending Approval\n\n"
        "Admin approval ke baad order process hoga.",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )

    await context.bot.send_message(
        ADMIN_ID,
        "❤️ NEW LIKE ORDER\n\n"
        f"Order: `{order_id}`\n"
        f"User ID: `{update.effective_user.id}`\n"
        f"Username: @{update.effective_user.username or 'none'}\n"
        f"Plan: {p['name']}\n"
        f"UID: `{uid}`\n"
        f"Amount: ₹{p['price']:.2f}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"like_ok:{order_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"like_no:{order_id}"),
            ]
        ]),
    )

async def like_admin_callback(update, context):
    q = update.callback_query
    await q.answer()

    if q.from_user.id != ADMIN_ID:
        return

    action, order_id = q.data.split(":", 1)

    con = connect()
    row = con.execute(
        "SELECT * FROM orders WHERE id=?",
        (order_id,),
    ).fetchone()

    if not row:
        con.close()
        await q.message.reply_text("❌ Order not found.")
        return

    if row["status"] != "Pending Approval":
        con.close()
        await q.message.reply_text(f"ℹ️ Already handled: {row['status']}")
        return

    if action == "like_ok":
        approved = now()
        expires = approved + timedelta(days=1)

        con.execute(
            """UPDATE orders SET status='Active',
               approved_at=?,expires_at=? WHERE id=?""",
            (approved.isoformat(), expires.isoformat(), order_id),
        )
        con.commit()
        con.close()

        await q.message.edit_text(
            q.message.text + "\n\n✅ APPROVED — Active",
            reply_markup=None,
        )

        await context.bot.send_message(
            row["user_id"],
            "✅ Order approved!\n\n"
            f"Order: {order_id}\n"
            f"UID: {row['uid']}\n"
            "Status: Active\n\n"
            "Service processing/fulfilment authorized order ke according hoga.",
        )

    else:
        con.execute(
            "UPDATE orders SET status='Rejected' WHERE id=?",
            (order_id,),
        )
        con.commit()
        con.close()

        # Refund reserved amount.
        change_balance(
            row["user_id"],
            float(row["amount"]),
            "Like order refund",
            order_id,
        )

        await q.message.edit_text(
            q.message.text + "\n\n❌ REJECTED — Amount refunded",
            reply_markup=None,
        )

        await context.bot.send_message(
            row["user_id"],
            "❌ Order rejected.\n\n"
            f"Order: {order_id}\n"
            f"Refund: ₹{row['amount']:.2f}\n"
            "Refund wallet me add kar diya gaya.",
        )

# =========================================================
# ORDERS
# =========================================================

async def my_orders(update, context):
    clear_state(context)
    con = connect()
    rows = con.execute(
        """SELECT o.*,p.name,p.days,p.daily_likes
           FROM orders o LEFT JOIN plans p ON p.code=o.plan_code
           WHERE o.user_id=? ORDER BY o.created_at DESC LIMIT 15""",
        (update.effective_user.id,),
    ).fetchall()
    con.close()

    if not rows:
        await update.message.reply_text(
            "📦 Abhi koi order nahi hai.",
            reply_markup=main_keyboard(),
        )
        return

    lines = ["📦 MY ORDERS\n"]
    for r in rows:
        lines.append(
            f"🆔 {r['id']}\n"
            f"Plan: {r['name'] or r['plan_code']}\n"
            f"UID: {r['uid']}\n"
            f"Amount: ₹{r['amount']:.2f}\n"
            f"Status: {r['status']}\n"
            f"Start: {fmt_date(r['approved_at'])}\n"
            f"Expiry: {fmt_date(r['expires_at'])}\n"
        )

    await update.message.reply_text("\n".join(lines), reply_markup=main_keyboard())

# =========================================================
# REFERRAL
# =========================================================

async def referral(update, context):
    clear_state(context)
    uid = update.effective_user.id
    reward = float(get_setting("referral_reward", "2"))

    con = connect()
    rows = con.execute(
        "SELECT * FROM referrals WHERE referrer_id=? ORDER BY id DESC",
        (uid,),
    ).fetchall()
    con.close()

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=ref_{uid}"

    await update.message.reply_text(
        "🎁 REFERRAL\n\n"
        f"Your link:\n{link}\n\n"
        f"Reward: ₹{reward:.2f}\n"
        f"Total referrals: {len(rows)}\n"
        f"Verified/Paid: {sum(1 for r in rows if r['status']=='paid')}\n\n"
        "Referral reward tabhi count hoga jab referred user required channels join kare.",
        reply_markup=main_keyboard(),
    )

async def process_referral_if_ready(context, referred_id):
    con = connect()
    row = con.execute(
        "SELECT * FROM referrals WHERE referred_id=? AND status='pending'",
        (referred_id,),
    ).fetchone()
    con.close()

    if not row:
        return False

    if not await channels_joined(context, referred_id):
        return False

    reward = float(get_setting("referral_reward", "2"))

    con = connect()
    con.execute(
        "UPDATE referrals SET status='paid',reward=?,paid_at=? WHERE id=?",
        (reward, now_text(), row["id"]),
    )
    con.commit()
    con.close()

    ok, _ = change_balance(
        row["referrer_id"],
        reward,
        "Referral reward",
        f"referral:{referred_id}",
    )
    return ok

# =========================================================
# SUPPORT
# =========================================================

async def support(update, context):
    clear_state(context)
    await update.message.reply_text(
        f"🛟 SUPPORT\n\nContact: {SUPPORT_USERNAME}",
        reply_markup=main_keyboard(),
    )

# =========================================================
# CHECK UID
# =========================================================

async def check_uid_start(update, context):
    clear_state(context)
    context.user_data["state"] = "check_uid"
    await update.message.reply_text("🆔 Free Fire UID bhejo:")

async def handle_check_uid(update, context):
    uid = update.message.text.strip()
    if not uid.isdigit():
        await update.message.reply_text("❌ Numeric UID bhejo.")
        return

    clear_state(context)

    try:
        r = requests.get(
            INFO_API,
            params={"uid": uid},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        await update.message.reply_text(
            "❌ UID API abhi available nahi hai. Thodi der baad try karo."
        )
        return

    if not isinstance(data, dict):
        await update.message.reply_text("❌ Invalid API response.")
        return

    # Keep this generic because API response fields can change.
    name = data.get("name") or data.get("nickname") or data.get("player_name") or "N/A"
    region = data.get("region") or data.get("server") or "N/A"
    level = data.get("level") or data.get("player_level") or "N/A"

    await update.message.reply_text(
        "🆔 ACCOUNT INFO\n\n"
        f"UID: {uid}\n"
        f"Name: {name}\n"
        f"Region: {region}\n"
        f"Level: {level}",
        reply_markup=main_keyboard(),
    )

# =========================================================
# CC STORE - AUTHORIZED DIGITAL STOCK ONLY
# =========================================================

async def cc_store(update, context):
    clear_state(context)
    name = get_setting("cc_name", "Digital Code")
    price = float(get_setting("cc_price", "100"))
    value = get_setting("cc_value", "₹3,000 value")
    desc = get_setting("cc_description", "")

    con = connect()
    item = con.execute(
        "SELECT * FROM cc_items WHERE active=1 ORDER BY id LIMIT 1"
    ).fetchone()
    stock = con.execute(
        "SELECT COUNT(*) AS c FROM cc_stock WHERE status='available'"
    ).fetchone()["c"]
    con.close()

    if item:
        name = item["name"]
        price = float(item["price"])
        value = item["value_text"]
        desc = item["description"]

    await update.message.reply_text(
        "🏪 CC STORE\n\n"
        f"📦 {name}\n"
        f"💰 Price: ₹{price:.2f}\n"
        f"🎁 Value: {value}\n"
        f"📦 Stock: {stock}\n\n"
        f"{desc}\n\n"
        "⚠️ Only authorized digital codes/items are supported.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Buy", callback_data="cc_buy")],
        ]),
    )

async def cc_buy(update, context):
    q = update.callback_query
    await q.answer()

    con = connect()
    item = con.execute(
        "SELECT * FROM cc_items WHERE active=1 ORDER BY id LIMIT 1"
    ).fetchone()
    stock = con.execute(
        "SELECT id,code FROM cc_stock WHERE status='available' ORDER BY id LIMIT 1"
    ).fetchone()
    con.close()

    if not item or not stock:
        await q.message.reply_text("❌ Abhi stock available nahi hai.")
        return

    price = float(item["price"])

    if balance(q.from_user.id) < price:
        await q.message.reply_text(
            f"❌ Balance low.\nRequired: ₹{price:.2f}\n"
            f"Balance: ₹{balance(q.from_user.id):.2f}"
        )
        return

    # Atomic sale.
    con = connect()
    con.execute("BEGIN IMMEDIATE")
    stock2 = con.execute(
        "SELECT id,code FROM cc_stock WHERE status='available' ORDER BY id LIMIT 1"
    ).fetchone()
    if not stock2:
        con.rollback()
        con.close()
        await q.message.reply_text("❌ Stock just sold out.")
        return

    row = con.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (q.from_user.id,),
    ).fetchone()
    if not row or float(row["balance"]) < price:
        con.rollback()
        con.close()
        await q.message.reply_text("❌ Balance low.")
        return

    new_balance = float(row["balance"]) - price
    con.execute(
        "UPDATE users SET balance=? WHERE user_id=?",
        (new_balance, q.from_user.id),
    )
    con.execute(
        """INSERT INTO transactions
           (user_id,kind,amount,balance_after,reference,created_at)
           VALUES(?,?,?,?,?,?)""",
        (q.from_user.id, "CC Store purchase", -price, new_balance, "CC", now_text()),
    )
    con.execute(
        """UPDATE cc_stock SET status='sold',sold_to=?,sold_at=?
           WHERE id=?""",
        (q.from_user.id, now_text(), stock2["id"]),
    )
    con.commit()
    con.close()

    await q.message.reply_text(
        "✅ PURCHASE SUCCESS\n\n"
        f"📦 {item['name']}\n"
        f"💰 Paid: ₹{price:.2f}\n\n"
        f"🔑 Code:\n`{stock2['code']}`\n\n"
        "Save this code securely.",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )

# =========================================================
# ADMIN
# =========================================================

def admin_only(user_id):
    return user_id == ADMIN_ID

async def admin_cmd(update, context):
    if not admin_only(update.effective_user.id):
        await update.message.reply_text("❌ Admin only.")
        return
    clear_state(context)
    await update.message.reply_text("🛠 ADMIN PANEL", reply_markup=admin_keyboard())

async def admin_callback(update, context):
    q = update.callback_query
    await q.answer()

    if not admin_only(q.from_user.id):
        return

    action = q.data

    if action == "adm_dashboard":
        con = connect()
        users = con.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        pending_utr = con.execute(
            "SELECT COUNT(*) c FROM deposits WHERE status='Pending'"
        ).fetchone()["c"]
        pending_likes = con.execute(
            "SELECT COUNT(*) c FROM orders WHERE status='Pending Approval'"
        ).fetchone()["c"]
        total_balance = con.execute(
            "SELECT COALESCE(SUM(balance),0) s FROM users"
        ).fetchone()["s"]
        con.close()

        await q.message.reply_text(
            "📊 DASHBOARD\n\n"
            f"👥 Users: {users}\n"
            f"💰 User balances: ₹{total_balance:.2f}\n"
            f"💳 Pending UTR: {pending_utr}\n"
            f"❤️ Pending Likes: {pending_likes}"
        )

    elif action == "adm_users":
        con = connect()
        rows = con.execute(
            "SELECT user_id,username,first_name,balance FROM users ORDER BY created_at DESC LIMIT 30"
        ).fetchall()
        con.close()

        text = "👥 USERS\n\n"
        for r in rows:
            text += (
                f"{r['user_id']} | @{r['username'] or '-'} | "
                f"₹{r['balance']:.2f}\n"
            )
        await q.message.reply_text(text[:4000] or "No users.")

    elif action == "adm_wallet":
        context.user_data["state"] = "admin_wallet_lookup"
        await q.message.reply_text("User Telegram ID bhejo:")

    elif action == "adm_add":
        context.user_data["state"] = "admin_add_user"
        await q.message.reply_text("Format: USER_ID AMOUNT\nExample: 123456789 100")

    elif action == "adm_deduct":
        context.user_data["state"] = "admin_deduct_user"
        await q.message.reply_text("Format: USER_ID AMOUNT\nExample: 123456789 50")

    elif action == "adm_tx":
        con = connect()
        rows = con.execute(
            """SELECT user_id,kind,amount,balance_after,created_at
               FROM transactions ORDER BY id DESC LIMIT 30"""
        ).fetchall()
        con.close()

        text = "📒 TRANSACTIONS\n\n"
        for r in rows:
            text += (
                f"{r['user_id']} | {r['kind']} | "
                f"{r['amount']:+.2f} | Bal ₹{r['balance_after']:.2f}\n"
            )
        await q.message.reply_text(text[:4000] or "No transactions.")

    elif action == "adm_utr":
        con = connect()
        rows = con.execute(
            """SELECT * FROM deposits
               WHERE status='Pending' ORDER BY created_at ASC LIMIT 20"""
        ).fetchall()
        con.close()

        if not rows:
            await q.message.reply_text("✅ No pending UTR.")
            return

        for r in rows:
            await q.message.reply_text(
                "💳 PENDING UTR\n\n"
                f"ID: {r['id']}\n"
                f"User: {r['user_id']}\n"
                f"Amount: ₹{r['amount']:.2f}\n"
                f"UTR: {r['utr']}",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"dep_ok:{r['id']}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"dep_no:{r['id']}"),
                    ]
                ]),
            )

    elif action == "adm_likes":
        con = connect()
        rows = con.execute(
            """SELECT o.*,p.name FROM orders o
               LEFT JOIN plans p ON p.code=o.plan_code
               WHERE o.status='Pending Approval'
               ORDER BY o.created_at ASC LIMIT 20"""
        ).fetchall()
        con.close()

        if not rows:
            await q.message.reply_text("✅ No pending like orders.")
            return

        for r in rows:
            await q.message.reply_text(
                "❤️ PENDING LIKE\n\n"
                f"Order: {r['id']}\n"
                f"User: {r['user_id']}\n"
                f"Plan: {r['name'] or r['plan_code']}\n"
                f"UID: {r['uid']}\n"
                f"Amount: ₹{r['amount']:.2f}",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"like_ok:{r['id']}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"like_no:{r['id']}"),
                    ]
                ]),
            )

    elif action == "adm_orders":
        con = connect()
        rows = con.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT 30"
        ).fetchall()
        con.close()

        text = "📦 ALL ORDERS\n\n"
        for r in rows:
            text += (
                f"{r['id']} | U:{r['user_id']} | UID:{r['uid']} | "
                f"{r['status']} | ₹{r['amount']:.2f}\n"
            )
        await q.message.reply_text(text[:4000] or "No orders.")

    elif action == "adm_refs":
        con = connect()
        rows = con.execute(
            "SELECT * FROM referrals ORDER BY id DESC LIMIT 30"
        ).fetchall()
        con.close()

        text = "🎁 REFERRALS\n\n"
        for r in rows:
            text += (
                f"Referrer: {r['referrer_id']} → {r['referred_id']} | "
                f"{r['status']} | ₹{r['reward']:.2f}\n"
            )
        await q.message.reply_text(text[:4000] or "No referrals.")

    elif action == "adm_reward":
        context.user_data["state"] = "admin_reward"
        await q.message.reply_text(
            f"Current reward: ₹{float(get_setting('referral_reward','2')):.2f}\n"
            "New reward amount bhejo:"
        )

    elif action == "adm_broadcast":
        context.user_data["state"] = "admin_broadcast"
        await q.message.reply_text("Broadcast message bhejo:")

    elif action == "adm_cc":
        name = get_setting("cc_name", "Digital Code")
        price = get_setting("cc_price", "100")
        value = get_setting("cc_value", "₹3,000 value")
        desc = get_setting("cc_description", "")
        await q.message.reply_text(
            "🏪 CC STORE SETTINGS\n\n"
            f"Name: {name}\n"
            f"Price: ₹{price}\n"
            f"Value: {value}\n"
            f"Description: {desc}\n\n"
            "Edit commands:\n"
            "/ccname NAME\n"
            "/ccprice AMOUNT\n"
            "/ccvalue TEXT\n"
            "/ccdesc TEXT"
        )

    elif action == "adm_stock":
        con = connect()
        count = con.execute(
            "SELECT COUNT(*) c FROM cc_stock WHERE status='available'"
        ).fetchone()["c"]
        con.close()
        await q.message.reply_text(
            f"📦 Available stock: {count}\n\n"
            "Stock add karne ke liye:\n"
            "/addstock CODE1\n"
            "/addstock CODE2"
        )

# =========================================================
# ADMIN DEPOSIT CALLBACK
# =========================================================

async def deposit_admin_callback(update, context):
    q = update.callback_query
    await q.answer()

    if not admin_only(q.from_user.id):
        return

    action, dep_id = q.data.split(":", 1)

    con = connect()
    row = con.execute(
        "SELECT * FROM deposits WHERE id=?",
        (dep_id,),
    ).fetchone()

    if not row:
        con.close()
        await q.message.reply_text("❌ Deposit not found.")
        return

    if row["status"] != "Pending":
        con.close()
        await q.message.reply_text(f"ℹ️ Already handled: {row['status']}")
        return

    if action == "dep_ok":
        con.execute(
            "UPDATE deposits SET status='Approved',reviewed_at=? WHERE id=?",
            (now_text(), dep_id),
        )
        con.commit()
        con.close()

        ok, new_bal = change_balance(
            row["user_id"],
            float(row["amount"]),
            "UPI deposit",
            dep_id,
        )
        if not ok:
            await q.message.reply_text("❌ Wallet credit failed.")
            return

        await q.message.edit_text(
            q.message.text + f"\n\n✅ APPROVED\nNew balance: ₹{new_bal:.2f}",
            reply_markup=None,
        )
        await context.bot.send_message(
            row["user_id"],
            f"✅ Deposit approved!\n\n"
            f"Amount: ₹{row['amount']:.2f}\n"
            f"New wallet balance: ₹{new_bal:.2f}",
        )

    else:
        con.execute(
            "UPDATE deposits SET status='Rejected',reviewed_at=? WHERE id=?",
            (now_text(), dep_id),
        )
        con.commit()
        con.close()

        await q.message.edit_text(
            q.message.text + "\n\n❌ REJECTED",
            reply_markup=None,
        )
        await context.bot.send_message(
            row["user_id"],
            f"❌ Deposit rejected.\n\nAmount: ₹{row['amount']:.2f}\nUTR: {row['utr']}",
        )

# =========================================================
# ADMIN TEXT ACTIONS
# =========================================================

async def admin_text_state(update, context):
    state = context.user_data.get("state")
    if not admin_only(update.effective_user.id) or not state:
        return False

    text = update.message.text.strip()

    if state == "admin_wallet_lookup":
        if not text.isdigit():
            await update.message.reply_text("❌ Numeric user ID bhejo.")
            return True
        uid = int(text)
        await admin_wallet_lookup(update, uid)
        clear_state(context)
        return True

    if state in ("admin_add_user", "admin_deduct_user"):
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ Format: USER_ID AMOUNT")
            return True
        try:
            uid = int(parts[0])
            amount = float(parts[1])
        except ValueError:
            await update.message.reply_text("❌ Invalid values.")
            return True

        if amount <= 0:
            await update.message.reply_text("❌ Amount > 0 hona chahiye.")
            return True

        if state == "admin_deduct_user":
            amount = -amount

        ok, new_bal = change_balance(
            uid,
            amount,
            "Admin balance",
            f"admin:{update.effective_user.id}",
        )
        clear_state(context)

        if not ok:
            await update.message.reply_text("❌ User nahi mila ya balance insufficient.")
        else:
            await update.message.reply_text(
                f"✅ Done.\nUser: {uid}\nNew balance: ₹{new_bal:.2f}"
            )
        return True

    if state == "admin_reward":
        try:
            reward = float(text)
        except ValueError:
            await update.message.reply_text("❌ Number bhejo.")
            return True
        if reward < 0 or reward > 10000:
            await update.message.reply_text("❌ Invalid reward.")
            return True
        set_setting("referral_reward", reward)
        clear_state(context)
        await update.message.reply_text(f"✅ Referral reward set: ₹{reward:.2f}")
        return True

    if state == "admin_broadcast":
        clear_state(context)
        con = connect()
        users = con.execute("SELECT user_id FROM users").fetchall()
        con.close()

        sent = 0
        failed = 0
        for row in users:
            try:
                await context.bot.send_message(row["user_id"], text)
                sent += 1
            except (Forbidden, BadRequest):
                failed += 1
            except Exception:
                failed += 1

        await update.message.reply_text(
            f"📢 Broadcast finished.\nSent: {sent}\nFailed: {failed}"
        )
        return True

    return False

async def admin_wallet_lookup(update, uid):
    con = connect()
    user = con.execute(
        "SELECT * FROM users WHERE user_id=?",
        (uid,),
    ).fetchone()
    tx = con.execute(
        """SELECT kind,amount,balance_after,created_at
           FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 10""",
        (uid,),
    ).fetchall()
    con.close()

    if not user:
        await update.message.reply_text("❌ User not found.")
        return

    text = (
        "💰 USER WALLET\n\n"
        f"User ID: {uid}\n"
        f"Username: @{user['username'] or '-'}\n"
        f"Balance: ₹{user['balance']:.2f}\n\n"
        "Transactions:\n"
    )
    for r in tx:
        text += f"{r['kind']} {r['amount']:+.2f} | {fmt_date(r['created_at'])}\n"

    await update.message.reply_text(text[:4000])

# =========================================================
# ADMIN COMMANDS FOR CC
# =========================================================

async def ccname_cmd(update, context):
    if not admin_only(update.effective_user.id):
        return
    value = update.message.text.partition(" ")[2].strip()
    if not value:
        await update.message.reply_text("Usage: /ccname NAME")
        return
    set_setting("cc_name", value)
    await update.message.reply_text("✅ CC name updated.")

async def ccprice_cmd(update, context):
    if not admin_only(update.effective_user.id):
        return
    value = update.message.text.partition(" ")[2].strip()
    try:
        price = float(value)
    except ValueError:
        await update.message.reply_text("Usage: /ccprice 100")
        return
    if price <= 0:
        await update.message.reply_text("❌ Invalid price.")
        return
    set_setting("cc_price", price)
    await update.message.reply_text("✅ CC price updated.")

async def ccvalue_cmd(update, context):
    if not admin_only(update.effective_user.id):
        return
    value = update.message.text.partition(" ")[2].strip()
    if not value:
        await update.message.reply_text("Usage: /ccvalue TEXT")
        return
    set_setting("cc_value", value)
    await update.message.reply_text("✅ CC value updated.")

async def ccdesc_cmd(update, context):
    if not admin_only(update.effective_user.id):
        return
    value = update.message.text.partition(" ")[2].strip()
    if not value:
        await update.message.reply_text("Usage: /ccdesc TEXT")
        return
    set_setting("cc_description", value)
    await update.message.reply_text("✅ CC description updated.")

async def addstock_cmd(update, context):
    if not admin_only(update.effective_user.id):
        return

    code = update.message.text.partition(" ")[2].strip()
    if not code:
        await update.message.reply_text("Usage: /addstock CODE")
        return

    con = connect()
    try:
        con.execute(
            "INSERT INTO cc_stock(item_id,code,status) VALUES(1,?,'available')",
            (code,),
        )
        con.commit()
        await update.message.reply_text("✅ Stock added.")
    except sqlite3.IntegrityError:
        await update.message.reply_text("❌ This code already exists.")
    finally:
        con.close()

# =========================================================
# ROUTER
# =========================================================

async def text_router(update, context):
    if not update.message or not update.effective_user:
        return

    ensure_user(update.effective_user)

    if await process_referral_if_ready(context, update.effective_user.id):
        pass

    if await admin_text_state(update, context):
        return

    state = context.user_data.get("state")

    if state == "deposit_amount":
        await handle_deposit_amount(update, context)
        return

    if state == "deposit_utr":
        await handle_deposit_utr(update, context)
        return

    if state == "like_uid":
        await handle_like_uid(update, context)
        return

    if state == "check_uid":
        await handle_check_uid(update, context)
        return

    text = update.message.text.strip()

    if text == "💰 Wallet":
        await wallet(update, context)
    elif text == "🛒 Buy Like":
        await buy_like(update, context)
    elif text == "📦 My Orders":
        await my_orders(update, context)
    elif text == "🎁 Referral":
        await referral(update, context)
    elif text == "🏪 CC Store":
        await cc_store(update, context)
    elif text == "🆔 Check UID":
        await check_uid_start(update, context)
    elif text == "🛟 Support":
        await support(update, context)
    else:
        await update.message.reply_text(
            "Menu se option choose karo.",
            reply_markup=main_keyboard(),
        )

# =========================================================
# CALLBACK ROUTER
# =========================================================

async def callback_router(update, context):
    q = update.callback_query
    data = q.data or ""

    if data == "check_join":
        await check_join(update, context)
    elif data.startswith("wallet_"):
        await wallet_callback(update, context)
    elif data.startswith("plan:"):
        await plan_callback(update, context)
    elif data.startswith("like_ok:") or data.startswith("like_no:"):
        await like_admin_callback(update, context)
    elif data.startswith("dep_ok:") or data.startswith("dep_no:"):
        await deposit_admin_callback(update, context)
    elif data == "cc_buy":
        await cc_buy(update, context)
    elif data.startswith("adm_"):
        await admin_callback(update, context)
    else:
        await q.answer()

# =========================================================
# COMMANDS
# =========================================================

async def cancel(update, context):
    clear_state(context)
    await update.message.reply_text(
        "❌ Cancelled.",
        reply_markup=main_keyboard(),
    )

# =========================================================
# MAIN
# =========================================================

def main():
    init_db()

    threading.Thread(target=run_web, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("acc", check_uid_start))
    app.add_handler(CommandHandler("ccname", ccname_cmd))
    app.add_handler(CommandHandler("ccprice", ccprice_cmd))
    app.add_handler(CommandHandler("ccvalue", ccvalue_cmd))
    app.add_handler(CommandHandler("ccdesc", ccdesc_cmd))
    app.add_handler(CommandHandler("addstock", addstock_cmd))

    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    print("VIP Bot started.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
