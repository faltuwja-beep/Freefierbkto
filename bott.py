import os
import sqlite3
import uuid
import threading
import requests

from datetime import datetime, timedelta, timezone

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

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable set karo."
    )


ADMIN_ID = int(
    os.getenv(
        "ADMIN_ID",
        "7161571409"
    )
)


UPI_ID = os.getenv(
    "UPI_ID",
    "sima6241@ptaxis"
)


SUPPORT_USERNAME = os.getenv(
    "SUPPORT_USERNAME",
    "@your_support"
)


DB_FILE = os.getenv(
    "DB_FILE",
    "vipbot.db"
)


# =========================================================
# FREE FIRE UID API
# =========================================================

INFO_API = os.getenv(
    "INFO_API",
    "https://ff-info-ro45.vercel.app/api"
)


INFO_API_KEY = os.getenv(
    "INFO_API_KEY",
    "Anurag"
)


# =========================================================
# REQUIRED CHANNELS
# =========================================================

REQUIRED_CHANNELS = [
    (
        "📢 Bot Like Proof",
        "@botlikeproof",
        "https://t.me/botlikeproof",
    ),
    (
        "💰 Earning With Ask 9",
        "@eraningwithask9",
        "https://t.me/eraningwithask9",
    ),
    (
        "🔥 Earning With Ask",
        "@eraningwithask",
        "https://t.me/eraningwithask",
    ),
]


# =========================================================
# WEB SERVER FOR RENDER
# =========================================================

web_app = Flask(__name__)


@web_app.get("/")
def home():
    return "VIP Bot is running", 200


@web_app.get("/health")
def health():
    return "OK", 200


def run_web():
    port = int(
        os.getenv(
            "PORT",
            "10000"
        )
    )

    web_app.run(
        host="0.0.0.0",
        port=port,
        use_reloader=False,
    )


# =========================================================
# DATABASE
# =========================================================

def connect():
    con = sqlite3.connect(
        DB_FILE,
        timeout=30,
        check_same_thread=False,
    )

    con.row_factory = sqlite3.Row

    con.execute(
        "PRAGMA busy_timeout=30000"
    )

    con.execute(
        "PRAGMA journal_mode=WAL"
    )

    return con


def init_db():

    con = connect()

    con.executescript(
        """

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
            utr TEXT NOT NULL UNIQUE,
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

        """
    )


    # -----------------------------------------------------
    # DEFAULT SETTINGS
    # -----------------------------------------------------

    defaults = [

        (
            "referral_reward",
            "2"
        ),

        (
            "cc_name",
            "Digital Code"
        ),

        (
            "cc_price",
            "100"
        ),

        (
            "cc_value",
            "₹3,000 Value"
        ),

        (
            "cc_description",
            "Authorized digital item/code."
        ),

    ]


    for key, value in defaults:

        con.execute(
            """
            INSERT OR IGNORE INTO settings
            (key,value)
            VALUES(?,?)
            """,
            (
                key,
                value,
            ),
        )


    # -----------------------------------------------------
    # DEFAULT PLANS
    # -----------------------------------------------------

    plans = [

        (
            "demo",
            "🎁 Demo",
            1,
            1,
            5
        ),

        (
            "starter",
            "🚀 Starter",
            220,
            15,
            59
        ),

        (
            "pro",
            "💎 Pro",
            220,
            30,
            99
        ),

    ]


    for (
        code,
        name,
        daily,
        days,
        price
    ) in plans:

        con.execute(
            """
            INSERT OR IGNORE INTO plans
            (
                code,
                name,
                daily_likes,
                days,
                price,
                active
            )
            VALUES(?,?,?,?,?,1)
            """,
            (
                code,
                name,
                daily,
                days,
                price,
            ),
        )


    # -----------------------------------------------------
    # DEFAULT CC ITEM
    # -----------------------------------------------------

    item = con.execute(
        "SELECT id FROM cc_items ORDER BY id LIMIT 1"
    ).fetchone()


    if not item:

        con.execute(
            """
            INSERT INTO cc_items
            (
                name,
                price,
                value_text,
                description,
                stock,
                active
            )
            VALUES(?,?,?,?,?,1)
            """,
            (
                "Digital Code",
                100,
                "₹3,000 Value",
                "Authorized digital item/code.",
                0,
            ),
        )


    con.commit()

    con.close()


# =========================================================
# TIME
# =========================================================

def now():
    return datetime.now(timezone.utc)


def now_text():
    return now().isoformat()


def fmt_date(value):

    if not value:
        return "-"

    try:

        dt = datetime.fromisoformat(value)

        return dt.astimezone().strftime(
            "%d-%m-%Y %I:%M %p"
        )

    except Exception:

        return value


# =========================================================
# SETTINGS
# =========================================================

def get_setting(
    key,
    default=""
):

    con = connect()

    row = con.execute(
        """
        SELECT value
        FROM settings
        WHERE key=?
        """,
        (key,),
    ).fetchone()

    con.close()

    if row:
        return row["value"]

    return default


def set_setting(
    key,
    value
):

    con = connect()

    con.execute(
        """
        INSERT INTO settings
        (key,value)
        VALUES(?,?)
        ON CONFLICT(key)
        DO UPDATE SET value=excluded.value
        """,
        (
            key,
            str(value),
        ),
    )

    con.commit()

    con.close()


# =========================================================
# USER
# =========================================================

def ensure_user(
    tg_user,
    referred_by=None
):

    con = connect()

    row = con.execute(
        """
        SELECT user_id
        FROM users
        WHERE user_id=?
        """,
        (
            tg_user.id,
        ),
    ).fetchone()


    if row:

        con.execute(
            """
            UPDATE users
            SET username=?,
                first_name=?
            WHERE user_id=?
            """,
            (
                tg_user.username or "",
                tg_user.first_name or "",
                tg_user.id,
            ),
        )


    else:

        valid_ref = None

        if (
            referred_by
            and referred_by != tg_user.id
        ):

            ref_exists = con.execute(
                """
                SELECT user_id
                FROM users
                WHERE user_id=?
                """,
                (
                    referred_by,
                ),
            ).fetchone()

            if ref_exists:

                valid_ref = referred_by


        con.execute(
            """
            INSERT INTO users
            (
                user_id,
                username,
                first_name,
                referred_by,
                created_at
            )
            VALUES(?,?,?,?,?)
            """,
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
                """
                INSERT OR IGNORE INTO referrals
                (
                    referrer_id,
                    referred_id,
                    status,
                    reward,
                    created_at
                )
                VALUES(?,?,?,?,?)
                """,
                (
                    valid_ref,
                    tg_user.id,
                    "pending",
                    0,
                    now_text(),
                ),
            )


    con.commit()

    con.close()


# =========================================================
# BALANCE
# =========================================================

def balance(
    user_id
):

    con = connect()

    row = con.execute(
        """
        SELECT balance
        FROM users
        WHERE user_id=?
        """,
        (
            user_id,
        ),
    ).fetchone()

    con.close()

    if not row:
        return 0.0

    return float(
        row["balance"]
    )


def change_balance(
    user_id,
    amount,
    kind,
    reference=""
):

    con = connect()

    try:

        con.execute(
            "BEGIN IMMEDIATE"
        )

        row = con.execute(
            """
            SELECT balance
            FROM users
            WHERE user_id=?
            """,
            (
                user_id,
            ),
        ).fetchone()


        if not row:

            con.rollback()

            return False, 0.0


        old = float(
            row["balance"]
        )

        new = old + float(amount)


        if new < -0.00001:

            con.rollback()

            return False, old


        con.execute(
            """
            UPDATE users
            SET balance=?
            WHERE user_id=?
            """,
            (
                new,
                user_id,
            ),
        )


        con.execute(
            """
            INSERT INTO transactions
            (
                user_id,
                kind,
                amount,
                balance_after,
                reference,
                created_at
            )
            VALUES(?,?,?,?,?,?)
            """,
            (
                user_id,
                kind,
                float(amount),
                new,
                reference,
                now_text(),
            ),
        )


        con.commit()

        return True, new


    except Exception:

        con.rollback()

        return False, balance(user_id)


    finally:

        con.close()


# =========================================================
# UI
# =========================================================

def main_keyboard():

    return ReplyKeyboardMarkup(
        [
            [
                "💰 Wallet",
                "🛒 Buy Like"
            ],
            [
                "📦 My Orders",
                "🎁 Referral"
            ],
            [
                "🏪 CC Store",
                "🆔 Check UID"
            ],
            [
                "🛟 Support"
            ],
        ],
        resize_keyboard=True,
    )


def admin_keyboard():

    return InlineKeyboardMarkup(
        [

            [
                InlineKeyboardButton(
                    "📊 Dashboard",
                    callback_data="adm_dashboard"
                ),

                InlineKeyboardButton(
                    "👥 Users",
                    callback_data="adm_users"
                ),
            ],

            [
                InlineKeyboardButton(
                    "💰 Wallet",
                    callback_data="adm_wallet"
                ),

                InlineKeyboardButton(
                    "➕ Add Balance",
                    callback_data="adm_add"
                ),
            ],

            [
                InlineKeyboardButton(
                    "➖ Deduct",
                    callback_data="adm_deduct"
                ),

                InlineKeyboardButton(
                    "📒 Transactions",
                    callback_data="adm_tx"
                ),
            ],

            [
                InlineKeyboardButton(
                    "💳 Pending UTR",
                    callback_data="adm_utr"
                ),

                InlineKeyboardButton(
                    "❤️ Pending Likes",
                    callback_data="adm_likes"
                ),
            ],

            [
                InlineKeyboardButton(
                    "📦 All Orders",
                    callback_data="adm_orders"
                ),

                InlineKeyboardButton(
                    "🎁 Referrals",
                    callback_data="adm_refs"
                ),
            ],

            [
                InlineKeyboardButton(
                    "🏪 CC Store",
                    callback_data="adm_cc"
                ),

                InlineKeyboardButton(
                    "📦 CC Stock",
                    callback_data="adm_stock"
                ),
            ],

            [
                InlineKeyboardButton(
                    "💸 Referral Reward",
                    callback_data="adm_reward"
                ),

                InlineKeyboardButton(
                    "📢 Broadcast",
                    callback_data="adm_broadcast"
                ),
            ],

        ]
    )


def clear_state(context):

    context.user_data.clear()


# =========================================================
# CHANNEL CHECK
# =========================================================

async def channels_joined(
    context,
    user_id
):

    for (
        _,
        chat,
        _
    ) in REQUIRED_CHANNELS:

        try:

            member = await context.bot.get_chat_member(
                chat,
                user_id
            )

            if member.status in (
                "left",
                "kicked"
            ):

                return False

        except Exception:

            # Don't falsely block if Telegram
            # cannot verify a channel.
            continue


    return True


async def join_required(
    update,
    context
):

    buttons = []

    for (
        name,
        _,
        url
    ) in REQUIRED_CHANNELS:

        buttons.append(
            [
                InlineKeyboardButton(
                    name,
                    url=url
                )
            ]
        )


    buttons.append(
        [
            InlineKeyboardButton(
                "✅ Check Join",
                callback_data="check_join"
            )
        ]
    )


    await update.effective_message.reply_text(
        "╔══════════════════════╗\n"
        "       📢 JOIN CHANNELS\n"
        "╚══════════════════════╝\n\n"
        "Bot use karne ke liye required "
        "channels join karo.\n\n"
        "Join karne ke baad:\n"
        "👇 Check Join dabao.",
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )


# =========================================================
# START
# =========================================================

async def start(
    update,
    context
):

    user = update.effective_user

    ref = None


    if context.args:

        arg = context.args[0]

        if arg.startswith("ref_"):

            try:
                ref = int(
                    arg[4:]
                )

            except ValueError:

                ref = None


    ensure_user(
        user,
        ref
    )

    clear_state(context)


    if not await channels_joined(
        context,
        user.id
    ):

        await join_required(
            update,
            context
        )

        return


    await update.message.reply_text(
        "╔══════════════════════════╗\n"
        "      🔥 VIP GAMING BOT 🔥\n"
        "╚══════════════════════════╝\n\n"

        f"👋 Welcome, {user.first_name or 'Gamer'}!\n\n"

        f"💰 Wallet Balance: "
        f"₹{balance(user.id):.2f}\n\n"

        "🎮 Free Fire Services\n"
        "❤️ Like Plans\n"
        "🆔 UID Information\n"
        "🏪 Digital Store\n"
        "🎁 Referral Rewards\n\n"

        "👇 Neeche menu se option choose karo.",
        reply_markup=main_keyboard(),
    )


# =========================================================
# CHECK JOIN
# =========================================================

async def check_join(
    update,
    context
):

    q = update.callback_query

    await q.answer()


    if await channels_joined(
        context,
        q.from_user.id
    ):

        await q.message.reply_text(
            "╔══════════════════════╗\n"
            "       ✅ VERIFIED\n"
            "╚══════════════════════╝\n\n"
            "Channel verification complete.\n\n"
            "Ab bot use kar sakte ho.",
            reply_markup=main_keyboard(),
        )

    else:

        await q.message.reply_text(
            "❌ Verification failed.\n\n"
            "Required channels join karke "
            "dobara Check Join dabao."
        )


# =========================================================
# WALLET
# =========================================================

async def wallet(
    update,
    context
):

    clear_state(context)

    uid = update.effective_user.id

    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "        💰 WALLET\n"
        "╚══════════════════════╝\n\n"

        f"💵 Balance: ₹{balance(uid):.2f}\n\n"

        "Wallet options:",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ Add Money",
                        callback_data="wallet_add"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📒 Transactions",
                        callback_data="wallet_tx"
                    )
                ],
            ]
        ),
    )


async def wallet_callback(
    update,
    context
):

    q = update.callback_query

    await q.answer()


    if q.data == "wallet_add":

        clear_state(context)

        context.user_data[
            "state"
        ] = "deposit_amount"


        await q.message.reply_text(
            "╔══════════════════════╗\n"
            "       ➕ ADD MONEY\n"
            "╚══════════════════════╝\n\n"

            f"💳 UPI ID:\n"
            f"`{UPI_ID}`\n\n"

            "Amount bhejo.\n\n"
            "Example:\n"
            "`100`",
            parse_mode="Markdown",
        )


    elif q.data == "wallet_tx":

        con = connect()

        rows = con.execute(
            """
            SELECT
                kind,
                amount,
                balance_after,
                reference,
                created_at
            FROM transactions
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT 10
            """,
            (
                q.from_user.id,
            ),
        ).fetchall()

        con.close()


        if not rows:

            await q.message.reply_text(
                "📒 Abhi koi transaction nahi hai."
            )

            return


        lines = [
            "╔══════════════════════╗",
            "      📒 TRANSACTIONS",
            "╚══════════════════════╝",
            "",
        ]


        for r in rows:

            sign = (
                "+"
                if r["amount"] >= 0
                else ""
            )

            lines.append(
                f"• {r['kind']}\n"
                f"  Amount: {sign}₹{r['amount']:.2f}\n"
                f"  Balance: ₹{r['balance_after']:.2f}\n"
                f"  {fmt_date(r['created_at'])}\n"
            )


        await q.message.reply_text(
            "\n".join(lines)
        )


# =========================================================
# DEPOSIT
# =========================================================

async def handle_deposit_amount(
    update,
    context
):

    text = update.message.text.strip()


    try:

        amount = float(text)

    except ValueError:

        await update.message.reply_text(
            "❌ Valid amount bhejo.\n"
            "Example: 100"
        )

        return


    if (
        amount < 1
        or amount > 100000
    ):

        await update.message.reply_text(
            "❌ Amount ₹1 se ₹100000 ke "
            "beech hona chahiye."
        )

        return


    context.user_data[
        "deposit_amount_value"
    ] = amount

    context.user_data[
        "state"
    ] = "deposit_utr"


    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "       💳 PAYMENT\n"
        "╚══════════════════════╝\n\n"

        f"💰 Amount: ₹{amount:.2f}\n\n"

        f"UPI ID:\n"
        f"`{UPI_ID}`\n\n"

        "Payment complete karo.\n"
        "Uske baad UTR / Transaction ID bhejo.",
        parse_mode="Markdown",
    )


async def handle_deposit_utr(
    update,
    context
):

    utr = update.message.text.strip()


    if (
        len(utr) < 4
        or len(utr) > 100
    ):

        await update.message.reply_text(
            "❌ Valid UTR/Transaction ID bhejo."
        )

        return


    amount = float(
        context.user_data.get(
            "deposit_amount_value",
            0
        )
    )


    if amount <= 0:

        clear_state(context)

        await update.message.reply_text(
            "❌ Session expired.\n"
            "Wallet → Add Money dobara karo."
        )

        return


    dep_id = (
        "DEP-"
        + uuid.uuid4().hex[:10].upper()
    )


    con = connect()


    try:

        con.execute(
            """
            INSERT INTO deposits
            (
                id,
                user_id,
                amount,
                utr,
                status,
                created_at
            )
            VALUES(?,?,?,?,?,?)
            """,
            (
                dep_id,
                update.effective_user.id,
                amount,
                utr,
                "Pending",
                now_text(),
            ),
        )

        con.commit()


    except sqlite3.IntegrityError:

        con.close()

        await update.message.reply_text(
            "❌ Ye UTR already submit ho chuka hai."
        )

        return


    finally:

        try:
            con.close()
        except Exception:
            pass


    clear_state(context)


    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "       ✅ UTR SUBMITTED\n"
        "╚══════════════════════╝\n\n"

        f"💰 Amount: ₹{amount:.2f}\n"
        f"🧾 UTR: {utr}\n"
        f"🆔 ID: {dep_id}\n\n"

        "Admin verification ke baad "
        "wallet credit hoga.",
        reply_markup=main_keyboard(),
    )


    try:

        await context.bot.send_message(
            ADMIN_ID,

            "╔══════════════════════╗\n"
            "       💳 NEW UTR\n"
            "╚══════════════════════╝\n\n"

            f"🆔 Deposit: `{dep_id}`\n"
            f"👤 User ID: `{update.effective_user.id}`\n"
            f"👤 Username: "
            f"@{update.effective_user.username or 'none'}\n"
            f"💰 Amount: ₹{amount:.2f}\n"
            f"🧾 UTR: `{utr}`",

            parse_mode="Markdown",

            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Approve",
                            callback_data=f"dep_ok:{dep_id}"
                        ),

                        InlineKeyboardButton(
                            "❌ Reject",
                            callback_data=f"dep_no:{dep_id}"
                        ),
                    ]
                ]
            ),
        )

    except Exception as e:

        print(
            "ADMIN UTR SEND ERROR:",
            e
        )


# =========================================================
# BUY LIKE
# =========================================================

async def buy_like(
    update,
    context
):

    clear_state(context)


    if not await channels_joined(
        context,
        update.effective_user.id
    ):

        await join_required(
            update,
            context
        )

        return


    con = connect()

    rows = con.execute(
        """
        SELECT *
        FROM plans
        WHERE active=1
        ORDER BY price ASC
        """
    ).fetchall()

    con.close()


    buttons = []


    for p in rows:

        buttons.append(
            [
                InlineKeyboardButton(
                    f"{p['name']} • ₹{p['price']}",
                    callback_data=f"plan:{p['code']}"
                )
            ]
        )


    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "       ❤️ LIKE PLANS\n"
        "╚══════════════════════╝\n\n"

        "👇 Apna plan select karo.\n\n"
        "Payment wallet se reserve hoga.\n"
        "Admin approval ke baad order active hoga.",

        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )


# =========================================================
# PLAN
# =========================================================

async def plan_callback(
    update,
    context
):

    q = update.callback_query

    await q.answer()


    code = q.data.split(
        ":",
        1
    )[1]


    con = connect()

    p = con.execute(
        """
        SELECT *
        FROM plans
        WHERE code=?
        AND active=1
        """,
        (
            code,
        ),
    ).fetchone()

    con.close()


    if not p:

        await q.message.reply_text(
            "❌ Plan unavailable."
        )

        return


    # -----------------------------------------------------
    # DEMO LIMIT
    # -----------------------------------------------------

    if code == "demo":

        con = connect()

        since = (
            now()
            - timedelta(hours=24)
        ).isoformat()


        row = con.execute(
            """
            SELECT id
            FROM orders
            WHERE user_id=?
            AND plan_code='demo'
            AND created_at>=?
            AND status NOT IN
            ('Rejected','Cancelled')
            """,
            (
                q.from_user.id,
                since,
            ),
        ).fetchone()

        con.close()


        if row:

            await q.message.reply_text(
                "⏳ Demo already used/requested "
                "in the last 24 hours."
            )

            return


    current_balance = balance(
        q.from_user.id
    )


    if current_balance < float(
        p["price"]
    ):

        await q.message.reply_text(
            "╔══════════════════════╗\n"
            "       ❌ LOW BALANCE\n"
            "╚══════════════════════╝\n\n"

            f"💰 Required: ₹{p['price']:.2f}\n"
            f"💵 Balance: ₹{current_balance:.2f}\n\n"

            "Wallet → Add Money karo."
        )

        return


    context.user_data[
        "state"
    ] = "like_uid"


    context.user_data[
        "plan_code"
    ] = code


    await q.message.reply_text(
        "╔══════════════════════╗\n"
        "       ❤️ PLAN SELECTED\n"
        "╚══════════════════════╝\n\n"

        f"📦 {p['name']}\n"
        f"❤️ Daily Likes: {p['daily_likes']}\n"
        f"📅 Duration: {p['days']} days\n"
        f"💰 Price: ₹{p['price']:.2f}\n\n"

        "🆔 Ab Free Fire UID bhejo:"
    )


# =========================================================
# LIKE UID
# =========================================================

async def handle_like_uid(
    update,
    context
):

    uid = update.message.text.strip()


    if (
        not uid.isdigit()
        or not (
            5 <= len(uid) <= 15
        )
    ):

        await update.message.reply_text(
            "❌ Valid numeric Free Fire UID bhejo."
        )

        return


    code = context.user_data.get(
        "plan_code"
    )


    if not code:

        clear_state(context)

        await update.message.reply_text(
            "❌ Session expired.\n"
            "Buy Like dobara karo."
        )

        return


    con = connect()

    p = con.execute(
        """
        SELECT *
        FROM plans
        WHERE code=?
        AND active=1
        """,
        (
            code,
        ),
    ).fetchone()

    con.close()


    if not p:

        clear_state(context)

        await update.message.reply_text(
            "❌ Plan unavailable."
        )

        return


    price = float(
        p["price"]
    )


    # -----------------------------------------------------
    # RESERVE MONEY
    # -----------------------------------------------------

    ok, new_balance = change_balance(
        update.effective_user.id,
        -price,
        "Like order reserve",
        "pending-order",
    )


    if not ok:

        clear_state(context)

        await update.message.reply_text(
            "❌ Wallet balance insufficient."
        )

        return


    order_id = (
        "ORD-"
        + uuid.uuid4().hex[:10].upper()
    )


    con = connect()


    try:

        con.execute(
            """
            INSERT INTO orders
            (
                id,
                user_id,
                plan_code,
                uid,
                amount,
                status,
                created_at,
                note
            )
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                order_id,
                update.effective_user.id,
                code,
                uid,
                price,
                "Pending Approval",
                now_text(),
                "",
            ),
        )

        con.commit()


    except Exception:

        con.close()

        # Refund if order insertion failed.
        change_balance(
            update.effective_user.id,
            price,
            "Order creation refund",
            order_id,
        )

        clear_state(context)

        await update.message.reply_text(
            "❌ Order create nahi ho saka.\n"
            "Amount wallet me refund kar diya gaya."
        )

        return


    con.close()

    clear_state(context)


    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "       ✅ ORDER CREATED\n"
        "╚══════════════════════╝\n\n"

        f"🆔 Order: `{order_id}`\n"
        f"🎮 UID: `{uid}`\n"
        f"💰 Amount: ₹{price:.2f}\n"
        "📌 Status: Pending Approval\n\n"

        "Admin approval ke baad order process hoga.",

        parse_mode="Markdown",

        reply_markup=main_keyboard(),
    )


    try:

        await context.bot.send_message(
            ADMIN_ID,

            "╔══════════════════════╗\n"
            "       ❤️ NEW LIKE ORDER\n"
            "╚══════════════════════╝\n\n"

            f"🆔 Order: `{order_id}`\n"
            f"👤 User: `{update.effective_user.id}`\n"
            f"👤 Username: "
            f"@{update.effective_user.username or 'none'}\n"
            f"📦 Plan: {p['name']}\n"
            f"🎮 UID: `{uid}`\n"
            f"💰 Amount: ₹{price:.2f}",

            parse_mode="Markdown",

            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Approve",
                            callback_data=f"like_ok:{order_id}"
                        ),

                        InlineKeyboardButton(
                            "❌ Reject",
                            callback_data=f"like_no:{order_id}"
                        ),
                    ]
                ]
            ),
        )

    except Exception as e:

        print(
            "ADMIN LIKE SEND ERROR:",
            e
        )


# =========================================================
# ADMIN LIKE
# =========================================================

async def like_admin_callback(
    update,
    context
):

    q = update.callback_query

    await q.answer()


    if q.from_user.id != ADMIN_ID:

        return


    action, order_id = q.data.split(
        ":",
        1
    )


    con = connect()

    row = con.execute(
        """
        SELECT *
        FROM orders
        WHERE id=?
        """,
        (
            order_id,
        ),
    ).fetchone()


    if not row:

        con.close()

        await q.message.reply_text(
            "❌ Order not found."
        )

        return


    if row["status"] != "Pending Approval":

        con.close()

        await q.message.reply_text(
            f"ℹ️ Already handled: "
            f"{row['status']}"
        )

        return


    # -----------------------------------------------------
    # APPROVE
    # -----------------------------------------------------

    if action == "like_ok":

        approved = now()

        expires = approved + timedelta(
            days=1
        )


        con.execute(
            """
            UPDATE orders
            SET status='Active',
                approved_at=?,
                expires_at=?
            WHERE id=?
            """,
            (
                approved.isoformat(),
                expires.isoformat(),
                order_id,
            ),
        )

        con.commit()

        con.close()


        await q.message.edit_text(
            q.message.text
            + "\n\n"
            "✅ APPROVED — Active",
            reply_markup=None,
        )


        try:

            await context.bot.send_message(
                row["user_id"],

                "╔══════════════════════╗\n"
                "       ✅ ORDER ACTIVE\n"
                "╚══════════════════════╝\n\n"

                f"🆔 Order: {order_id}\n"
                f"🎮 UID: {row['uid']}\n"
                "📌 Status: Active\n\n"

                "Service processing/fulfilment "
                "authorized order ke according hoga."
            )

        except Exception as e:

            print(
                "USER APPROVE SEND ERROR:",
                e
            )


    # -----------------------------------------------------
    # REJECT
    # -----------------------------------------------------

    else:

        con.execute(
            """
            UPDATE orders
            SET status='Rejected'
            WHERE id=?
            """,
            (
                order_id,
            ),
        )

        con.commit()

        con.close()


        change_balance(
            row["user_id"],
            float(row["amount"]),
            "Like order refund",
            order_id,
        )


        await q.message.edit_text(
            q.message.text
            + "\n\n"
            "❌ REJECTED — Amount refunded",
            reply_markup=None,
        )


        try:

            await context.bot.send_message(
                row["user_id"],

                "╔══════════════════════╗\n"
                "       ❌ ORDER REJECTED\n"
                "╚══════════════════════╝\n\n"

                f"🆔 Order: {order_id}\n"
                f"💰 Refund: ₹{row['amount']:.2f}\n\n"

                "Amount wallet me refund kar diya gaya."
            )

        except Exception as e:

            print(
                "USER REFUND SEND ERROR:",
                e
            )


# =========================================================
# MY ORDERS
# =========================================================

async def my_orders(
    update,
    context
):

    clear_state(context)


    con = connect()

    rows = con.execute(
        """
        SELECT
            o.*,
            p.name,
            p.days,
            p.daily_likes
        FROM orders o
        LEFT JOIN plans p
            ON p.code=o.plan_code
        WHERE o.user_id=?
        ORDER BY o.created_at DESC
        LIMIT 15
        """,
        (
            update.effective_user.id,
        ),
    ).fetchall()

    con.close()


    if not rows:

        await update.message.reply_text(
            "📦 Abhi koi order nahi hai.",
            reply_markup=main_keyboard(),
        )

        return


    lines = [
        "╔══════════════════════╗",
        "        📦 MY ORDERS",
        "╚══════════════════════╝",
        "",
    ]


    for r in rows:

        lines.append(
            f"🆔 {r['id']}\n"
            f"📦 Plan: {r['name'] or r['plan_code']}\n"
            f"🎮 UID: {r['uid']}\n"
            f"💰 Amount: ₹{r['amount']:.2f}\n"
            f"📌 Status: {r['status']}\n"
            f"🕐 Start: {fmt_date(r['approved_at'])}\n"
            f"⏳ Expiry: {fmt_date(r['expires_at'])}\n"
        )


    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=main_keyboard(),
    )


# =========================================================
# REFERRAL
# =========================================================

async def referral(
    update,
    context
):

    clear_state(context)


    uid = update.effective_user.id

    reward = float(
        get_setting(
            "referral_reward",
            "2"
        )
    )


    con = connect()

    rows = con.execute(
        """
        SELECT *
        FROM referrals
        WHERE referrer_id=?
        ORDER BY id DESC
        """,
        (
            uid,
        ),
    ).fetchall()

    con.close()


    bot_info = await context.bot.get_me()

    bot_username = bot_info.username


    link = (
        f"https://t.me/"
        f"{bot_username}"
        f"?start=ref_{uid}"
    )


    paid = sum(
        1
        for r in rows
        if r["status"] == "paid"
    )


    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "       🎁 REFERRAL\n"
        "╚══════════════════════╝\n\n"

        "🔗 Your Referral Link:\n"
        f"`{link}`\n\n"

        f"💸 Reward: ₹{reward:.2f}\n"
        f"👥 Total Referrals: {len(rows)}\n"
        f"✅ Paid Referrals: {paid}\n\n"

        "Friend ko link se bot start karvao.\n"
        "Required channels verification ke baad "
        "reward process hoga.",

        parse_mode="Markdown",

        reply_markup=main_keyboard(),
    )


async def process_referral_if_ready(
    context,
    referred_id
):

    con = connect()

    row = con.execute(
        """
        SELECT *
        FROM referrals
        WHERE referred_id=?
        AND status='pending'
        """,
        (
            referred_id,
        ),
    ).fetchone()

    con.close()


    if not row:

        return False


    if not await channels_joined(
        context,
        referred_id
    ):

        return False


    reward = float(
        get_setting(
            "referral_reward",
            "2"
        )
    )


    con = connect()

    con.execute(
        """
        UPDATE referrals
        SET status='paid',
            reward=?,
            paid_at=?
        WHERE id=?
        AND status='pending'
        """,
        (
            reward,
            now_text(),
            row["id"],
        ),
    )

    changed = con.total_changes

    con.commit()

    con.close()


    if changed == 0:

        return False


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

async def support(
    update,
    context
):

    clear_state(context)


    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "        🛟 SUPPORT\n"
        "╚══════════════════════╝\n\n"

        f"👨‍💻 Support: {SUPPORT_USERNAME}\n\n"

        "Problem ho to support se contact karo.",

        reply_markup=main_keyboard(),
    )


# =========================================================
# CHECK UID
# =========================================================

async def check_uid_start(
    update,
    context
):

    clear_state(context)


    context.user_data[
        "state"
    ] = "check_uid"


    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "         🆔 CHECK UID\n"
        "╚══════════════════════╝\n\n"

        "Free Fire UID bhejo.\n\n"

        "Example:\n"
        "`14307670967`\n\n"

        "⏳ Account information fetch hogi.",

        parse_mode="Markdown",
    )


# =========================================================
# UID API
# =========================================================

async def handle_check_uid(
    update,
    context
):

    uid = update.message.text.strip()


    # -----------------------------------------------------
    # UID VALIDATION
    # -----------------------------------------------------

    if not uid.isdigit():

        await update.message.reply_text(
            "❌ Invalid UID.\n\n"
            "Sirf numeric Free Fire UID bhejo."
        )

        return


    if not (
        5 <= len(uid) <= 15
    ):

        await update.message.reply_text(
            "❌ UID length invalid hai.\n\n"
            "Example:\n"
            "`14307670967`",
            parse_mode="Markdown",
        )

        return


    status_message = await update.message.reply_text(
        "🔎 UID information fetch ho rahi hai...\n"
        "⏳ Please wait..."
    )


    # -----------------------------------------------------
    # API REQUEST
    # -----------------------------------------------------

    try:

        response = requests.get(
            INFO_API,
            params={
                "uid": uid,
                "key": INFO_API_KEY,
            },
            timeout=20,
        )


        print(
            "UID API STATUS:",
            response.status_code
        )


        response.raise_for_status()


        data = response.json()


    except requests.exceptions.Timeout:

        await status_message.edit_text(
            "⏱️ UID API timeout ho gayi.\n\n"
            "Thodi der baad dobara try karo."
        )

        return


    except requests.exceptions.RequestException as e:

        print(
            "UID API REQUEST ERROR:",
            e
        )

        await status_message.edit_text(
            "❌ UID API connect nahi ho pa rahi.\n\n"
            "Thodi der baad try karo."
        )

        return


    except ValueError:

        await status_message.edit_text(
            "❌ API ne valid JSON response nahi diya."
        )

        return


    # -----------------------------------------------------
    # RESPONSE VALIDATION
    # -----------------------------------------------------

    if not isinstance(
        data,
        dict
    ):

        await status_message.edit_text(
            "❌ Invalid API response."
        )

        return


    # -----------------------------------------------------
    # BASIC INFO
    # -----------------------------------------------------

    basic = (
        data.get("basicInfo")
        or {}
    )


    social = (
        data.get("socialInfo")
        or {}
    )


    pet = (
        data.get("petInfo")
        or {}
    )


    clan = (
        data.get("clanBasicInfo")
        or {}
    )


    credit = (
        data.get("creditScoreInfo")
        or {}
    )


    # -----------------------------------------------------
    # BASIC FIELDS
    # -----------------------------------------------------

    nickname = (
        basic.get("nickname")
        or basic.get("name")
        or "Unknown"
    )


    region = (
        basic.get("region")
        or basic.get("server")
        or "Unknown"
    )


    level = (
        basic.get("level")
        or "N/A"
    )


    exp = (
        basic.get("exp")
        or "N/A"
    )


    rank = (
        basic.get("rank")
        or "N/A"
    )


    cs_rank = (
        basic.get("csRank")
        or "N/A"
    )


    max_rank = (
        basic.get("maxRank")
        or "N/A"
    )


    liked = (
        basic.get("liked")
        or 0
    )


    account_type = (
        basic.get("accountType")
        or "N/A"
    )


    release_version = (
        basic.get("releaseVersion")
        or "N/A"
    )


    # -----------------------------------------------------
    # EXTRA INFO
    # -----------------------------------------------------

    ranking_points = (
        basic.get("rankingPoints")
        or "N/A"
    )


    clan_name = (
        clan.get("clanName")
        or clan.get("name")
        or "No Clan"
    )


    clan_id = (
        clan.get("clanId")
        or clan.get("id")
        or "N/A"
    )


    pet_id = (
        pet.get("id")
        or "N/A"
    )


    language = (
        social.get("language")
        or "N/A"
    )


    signature = (
        social.get("signature")
        or "No signature"
    )


    credit_score = (
        credit.get("creditScore")
        or "N/A"
    )


    # -----------------------------------------------------
    # PRIME UID CARD
    # -----------------------------------------------------

    result = (

        "╔══════════════════════════╗\n"
        "       🎮 FREE FIRE INFO\n"
        "╚══════════════════════════╝\n\n"

        f"👤 Name: {nickname}\n"
        f"🆔 UID: `{uid}`\n"
        f"🌍 Region: {region}\n\n"

        "┏━━━━━━━━━━━━━━━━━━━━┓\n"
        "        📊 ACCOUNT\n"
        "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"

        f"⭐ Level: {level}\n"
        f"✨ EXP: {exp}\n"
        f"🏆 BR Rank: {rank}\n"
        f"⚔️ CS Rank: {cs_rank}\n"
        f"🏅 Max Rank: {max_rank}\n"
        f"❤️ Likes: {liked}\n"
        f"🏆 Ranking Points: {ranking_points}\n"
        f"💯 Credit Score: {credit_score}\n\n"

        "┏━━━━━━━━━━━━━━━━━━━━┓\n"
        "         👥 CLAN\n"
        "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"

        f"🏷️ Name: {clan_name}\n"
        f"🆔 ID: {clan_id}\n\n"

        "┏━━━━━━━━━━━━━━━━━━━━┓\n"
        "          🐾 PET\n"
        "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"

        f"🐾 Pet ID: {pet_id}\n\n"

        "┏━━━━━━━━━━━━━━━━━━━━┓\n"
        "         🌐 OTHER\n"
        "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"

        f"🌐 Language: {language}\n"
        f"📱 Version: {release_version}\n"
        f"📝 Signature: {signature}\n"
        f"🔐 Account Type: {account_type}\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 VIP Gaming Bot\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )


    try:

        await status_message.edit_text(
            result,
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )

    except BadRequest:

        await update.message.reply_text(
            result,
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )


    clear_state(context)


# =========================================================
# CC STORE
# =========================================================

async def cc_store(
    update,
    context
):

    clear_state(context)


    con = connect()


    item = con.execute(
        """
        SELECT *
        FROM cc_items
        WHERE active=1
        ORDER BY id
        LIMIT 1
        """
    ).fetchone()


    if item:

        name = item["name"]

        price = float(
            item["price"]
        )

        value = item[
            "value_text"
        ]

        desc = item[
            "description"
        ]

        stock = con.execute(
            """
            SELECT COUNT(*) AS c
            FROM cc_stock
            WHERE item_id=?
            AND status='available'
            """,
            (
                item["id"],
            ),
        ).fetchone()["c"]

    else:

        name = get_setting(
            "cc_name",
            "Digital Code"
        )

        price = float(
            get_setting(
                "cc_price",
                "100"
            )
        )

        value = get_setting(
            "cc_value",
            "₹3,000 Value"
        )

        desc = get_setting(
            "cc_description",
            ""
        )

        stock = 0


    con.close()


    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "        🏪 CC STORE\n"
        "╚══════════════════════╝\n\n"

        f"📦 Product: {name}\n"
        f"💰 Price: ₹{price:.2f}\n"
        f"🎁 Value: {value}\n"
        f"📦 Stock: {stock}\n\n"

        f"📝 {desc}\n\n"

        "⚠️ Only authorized digital "
        "codes/items are supported.",

        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🛒 Buy Now",
                        callback_data="cc_buy"
                    )
                ]
            ]
        ),
    )


# =========================================================
# CC BUY
# =========================================================

async def cc_buy(
    update,
    context
):

    q = update.callback_query

    await q.answer()


    con = connect()

    item = con.execute(
        """
        SELECT *
        FROM cc_items
        WHERE active=1
        ORDER BY id
        LIMIT 1
        """
    ).fetchone()


    if not item:

        con.close()

        await q.message.reply_text(
            "❌ Product unavailable."
        )

        return


    price = float(
        item["price"]
    )


    # -----------------------------------------------------
    # ATOMIC SALE
    # -----------------------------------------------------

    try:

        con.execute(
            "BEGIN IMMEDIATE"
        )


        stock = con.execute(
            """
            SELECT id,code
            FROM cc_stock
            WHERE item_id=?
            AND status='available'
            ORDER BY id
            LIMIT 1
            """,
            (
                item["id"],
            ),
        ).fetchone()


        if not stock:

            con.rollback()

            con.close()

            await q.message.reply_text(
                "❌ Abhi stock available nahi hai."
            )

            return


        user = con.execute(
            """
            SELECT balance
            FROM users
            WHERE user_id=?
            """,
            (
                q.from_user.id,
            ),
        ).fetchone()


        if (
            not user
            or float(user["balance"]) < price
        ):

            con.rollback()

            con.close()

            current = balance(
                q.from_user.id
            )

            await q.message.reply_text(
                "❌ Balance low.\n\n"
                f"Required: ₹{price:.2f}\n"
                f"Balance: ₹{current:.2f}"
            )

            return


        new_balance = (
            float(user["balance"])
            - price
        )


        con.execute(
            """
            UPDATE users
            SET balance=?
            WHERE user_id=?
            """,
            (
                new_balance,
                q.from_user.id,
            ),
        )


        con.execute(
            """
            INSERT INTO transactions
            (
                user_id,
                kind,
                amount,
                balance_after,
                reference,
                created_at
            )
            VALUES(?,?,?,?,?,?)
            """,
            (
                q.from_user.id,
                "CC Store purchase",
                -price,
                new_balance,
                "CC",
                now_text(),
            ),
        )


        con.execute(
            """
            UPDATE cc_stock
            SET status='sold',
                sold_to=?,
                sold_at=?
            WHERE id=?
            """,
            (
                q.from_user.id,
                now_text(),
                stock["id"],
            ),
        )


        con.commit()


    except Exception as e:

        print(
            "CC SALE ERROR:",
            e
        )

        con.rollback()

        con.close()

        await q.message.reply_text(
            "❌ Purchase failed."
        )

        return


    con.close()


    await q.message.reply_text(
        "╔══════════════════════╗\n"
        "      ✅ PURCHASE SUCCESS\n"
        "╚══════════════════════╝\n\n"

        f"📦 Product: {item['name']}\n"
        f"💰 Paid: ₹{price:.2f}\n\n"

        "🔑 Your Code:\n"
        f"`{stock['code']}`\n\n"

        "⚠️ Code ko securely save karo.",

        parse_mode="Markdown",

        reply_markup=main_keyboard(),
    )


# =========================================================
# ADMIN
# =========================================================

def admin_only(
    user_id
):

    return user_id == ADMIN_ID


async def admin_cmd(
    update,
    context
):

    if not admin_only(
        update.effective_user.id
    ):

        await update.message.reply_text(
            "❌ Admin only."
        )

        return


    clear_state(context)


    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "        🛠 ADMIN PANEL\n"
        "╚══════════════════════╝\n\n"
        "Admin controls:",
        reply_markup=admin_keyboard(),
    )


# =========================================================
# ADMIN CALLBACK
# =========================================================

async def admin_callback(
    update,
    context
):

    q = update.callback_query

    await q.answer()


    if not admin_only(
        q.from_user.id
    ):

        return


    action = q.data


    # -----------------------------------------------------
    # DASHBOARD
    # -----------------------------------------------------

    if action == "adm_dashboard":

        con = connect()


        users = con.execute(
            "SELECT COUNT(*) c FROM users"
        ).fetchone()["c"]


        pending_utr = con.execute(
            """
            SELECT COUNT(*) c
            FROM deposits
            WHERE status='Pending'
            """
        ).fetchone()["c"]


        pending_likes = con.execute(
            """
            SELECT COUNT(*) c
            FROM orders
            WHERE status='Pending Approval'
            """
        ).fetchone()["c"]


        total_balance = con.execute(
            """
            SELECT COALESCE(
                SUM(balance),
                0
            ) s
            FROM users
            """
        ).fetchone()["s"]


        total_deposits = con.execute(
            """
            SELECT COALESCE(
                SUM(amount),
                0
            ) s
            FROM deposits
            WHERE status='Approved'
            """
        ).fetchone()["s"]


        total_orders = con.execute(
            """
            SELECT COUNT(*) c
            FROM orders
            """
        ).fetchone()["c"]


        con.close()


        await q.message.reply_text(
            "╔══════════════════════╗\n"
            "        📊 DASHBOARD\n"
            "╚══════════════════════╝\n\n"

            f"👥 Users: {users}\n"
            f"💰 User Balances: ₹{float(total_balance):.2f}\n"
            f"💳 Approved Deposits: ₹{float(total_deposits):.2f}\n"
            f"📦 Total Orders: {total_orders}\n"
            f"⏳ Pending UTR: {pending_utr}\n"
            f"❤️ Pending Likes: {pending_likes}"
        )


    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    elif action == "adm_users":

        con = connect()

        rows = con.execute(
            """
            SELECT
                user_id,
                username,
                first_name,
                balance
            FROM users
            ORDER BY created_at DESC
            LIMIT 30
            """
        ).fetchall()

        con.close()


        if not rows:

            await q.message.reply_text(
                "No users."
            )

            return


        text = [
            "╔══════════════════════╗",
            "          👥 USERS",
            "╚══════════════════════╝",
            "",
        ]


        for r in rows:

            text.append(
                f"🆔 {r['user_id']}\n"
                f"👤 @{r['username'] or '-'}\n"
                f"💰 ₹{r['balance']:.2f}\n"
            )


        await q.message.reply_text(
            "\n".join(text)[:4000]
        )


    # -----------------------------------------------------
    # WALLET LOOKUP
    # -----------------------------------------------------

    elif action == "adm_wallet":

        context.user_data[
            "state"
        ] = "admin_wallet_lookup"


        await q.message.reply_text(
            "💰 User Telegram ID bhejo:"
        )


    # -----------------------------------------------------
    # ADD BALANCE
    # -----------------------------------------------------

    elif action == "adm_add":

        context.user_data[
            "state"
        ] = "admin_add_user"


        await q.message.reply_text(
            "➕ ADD BALANCE\n\n"
            "Format:\n"
            "`USER_ID AMOUNT`\n\n"
            "Example:\n"
            "`123456789 100`",
            parse_mode="Markdown",
        )


    # -----------------------------------------------------
    # DEDUCT
    # -----------------------------------------------------

    elif action == "adm_deduct":

        context.user_data[
            "state"
        ] = "admin_deduct_user"


        await q.message.reply_text(
            "➖ DEDUCT BALANCE\n\n"
            "Format:\n"
            "`USER_ID AMOUNT`\n\n"
            "Example:\n"
            "`123456789 50`",
            parse_mode="Markdown",
        )


    # -----------------------------------------------------
    # TRANSACTIONS
    # -----------------------------------------------------

    elif action == "adm_tx":

        con = connect()

        rows = con.execute(
            """
            SELECT
                user_id,
                kind,
                amount,
                balance_after,
                created_at
            FROM transactions
            ORDER BY id DESC
            LIMIT 30
            """
        ).fetchall()

        con.close()


        text = [
            "╔══════════════════════╗",
            "       📒 TRANSACTIONS",
            "╚══════════════════════╝",
            "",
        ]


        for r in rows:

            text.append(
                f"{r['user_id']} | "
                f"{r['kind']} | "
                f"{r['amount']:+.2f} | "
                f"₹{r['balance_after']:.2f}"
            )


        await q.message.reply_text(
            "\n".join(text)[:4000]
            or "No transactions."
        )


    # -----------------------------------------------------
    # UTR
    # -----------------------------------------------------

    elif action == "adm_utr":

        con = connect()

        rows = con.execute(
            """
            SELECT *
            FROM deposits
            WHERE status='Pending'
            ORDER BY created_at ASC
            LIMIT 20
            """
        ).fetchall()

        con.close()


        if not rows:

            await q.message.reply_text(
                "✅ No pending UTR."
            )

            return


        for r in rows:

            await q.message.reply_text(

                "╔══════════════════════╗\n"
                "        💳 PENDING UTR\n"
                "╚══════════════════════╝\n\n"

                f"🆔 ID: {r['id']}\n"
                f"👤 User: {r['user_id']}\n"
                f"💰 Amount: ₹{r['amount']:.2f}\n"
                f"🧾 UTR: {r['utr']}",

                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "✅ Approve",
                                callback_data=f"dep_ok:{r['id']}"
                            ),

                            InlineKeyboardButton(
                                "❌ Reject",
                                callback_data=f"dep_no:{r['id']}"
                            ),
                        ]
                    ]
                ),
            )


    # -----------------------------------------------------
    # PENDING LIKES
    # -----------------------------------------------------

    elif action == "adm_likes":

        con = connect()

        rows = con.execute(
            """
            SELECT
                o.*,
                p.name
            FROM orders o
            LEFT JOIN plans p
                ON p.code=o.plan_code
            WHERE o.status='Pending Approval'
            ORDER BY o.created_at ASC
            LIMIT 20
            """
        ).fetchall()

        con.close()


        if not rows:

            await q.message.reply_text(
                "✅ No pending like orders."
            )

            return


        for r in rows:

            await q.message.reply_text(

                "╔══════════════════════╗\n"
                "       ❤️ PENDING LIKE\n"
                "╚══════════════════════╝\n\n"

                f"🆔 Order: {r['id']}\n"
                f"👤 User: {r['user_id']}\n"
                f"📦 Plan: {r['name'] or r['plan_code']}\n"
                f"🎮 UID: {r['uid']}\n"
                f"💰 Amount: ₹{r['amount']:.2f}",

                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "✅ Approve",
                                callback_data=f"like_ok:{r['id']}"
                            ),

                            InlineKeyboardButton(
                                "❌ Reject",
                                callback_data=f"like_no:{r['id']}"
                            ),
                        ]
                    ]
                ),
            )


    # -----------------------------------------------------
    # ORDERS
    # -----------------------------------------------------

    elif action == "adm_orders":

        con = connect()

        rows = con.execute(
            """
            SELECT *
            FROM orders
            ORDER BY created_at DESC
            LIMIT 30
            """
        ).fetchall()

        con.close()


        text = [
            "╔══════════════════════╗",
            "        📦 ALL ORDERS",
            "╚══════════════════════╝",
            "",
        ]


        for r in rows:

            text.append(
                f"{r['id']} | "
                f"U:{r['user_id']} | "
                f"UID:{r['uid']} | "
                f"{r['status']} | "
                f"₹{r['amount']:.2f}"
            )


        await q.message.reply_text(
            "\n".join(text)[:4000]
            or "No orders."
        )


    # -----------------------------------------------------
    # REFERRALS
    # -----------------------------------------------------

    elif action == "adm_refs":

        con = connect()

        rows = con.execute(
            """
            SELECT *
            FROM referrals
            ORDER BY id DESC
            LIMIT 30
            """
        ).fetchall()

        con.close()


        text = [
            "╔══════════════════════╗",
            "        🎁 REFERRALS",
            "╚══════════════════════╝",
            "",
        ]


        for r in rows:

            text.append(
                f"👤 {r['referrer_id']} → "
                f"{r['referred_id']} | "
                f"{r['status']} | "
                f"₹{r['reward']:.2f}"
            )


        await q.message.reply_text(
            "\n".join(text)[:4000]
            or "No referrals."
        )


    # -----------------------------------------------------
    # REFERRAL REWARD
    # -----------------------------------------------------

    elif action == "adm_reward":

        context.user_data[
            "state"
        ] = "admin_reward"


        await q.message.reply_text(
            f"Current reward: "
            f"₹{float(get_setting('referral_reward','2')):.2f}\n\n"
            "New reward amount bhejo:"
        )


    # -----------------------------------------------------
    # BROADCAST
    # -----------------------------------------------------

    elif action == "adm_broadcast":

        context.user_data[
            "state"
        ] = "admin_broadcast"


        await q.message.reply_text(
            "📢 Broadcast message bhejo:"
        )


    # -----------------------------------------------------
    # CC
    # -----------------------------------------------------

    elif action == "adm_cc":

        name = get_setting(
            "cc_name",
            "Digital Code"
        )

        price = get_setting(
            "cc_price",
            "100"
        )

        value = get_setting(
            "cc_value",
            "₹3,000 Value"
        )

        desc = get_setting(
            "cc_description",
            ""
        )


        await q.message.reply_text(
            "╔══════════════════════╗\n"
            "        🏪 CC STORE\n"
            "╚══════════════════════╝\n\n"

            f"Name: {name}\n"
            f"Price: ₹{price}\n"
            f"Value: {value}\n"
            f"Description: {desc}\n\n"

            "Commands:\n"
            "/ccname NAME\n"
            "/ccprice AMOUNT\n"
            "/ccvalue TEXT\n"
            "/ccdesc TEXT"
        )


    # -----------------------------------------------------
    # STOCK
    # -----------------------------------------------------

    elif action == "adm_stock":

        con = connect()

        item = con.execute(
            """
            SELECT id
            FROM cc_items
            WHERE active=1
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()


        if item:

            count = con.execute(
                """
                SELECT COUNT(*) c
                FROM cc_stock
                WHERE item_id=?
                AND status='available'
                """,
                (
                    item["id"],
                ),
            ).fetchone()["c"]

        else:

            count = 0


        con.close()


        await q.message.reply_text(
            f"📦 Available Stock: {count}\n\n"
            "Stock add karne ke liye:\n"
            "/addstock CODE"
        )


# =========================================================
# DEPOSIT ADMIN
# =========================================================

async def deposit_admin_callback(
    update,
    context
):

    q = update.callback_query

    await q.answer()


    if not admin_only(
        q.from_user.id
    ):

        return


    action, dep_id = q.data.split(
        ":",
        1
    )


    con = connect()

    row = con.execute(
        """
        SELECT *
        FROM deposits
        WHERE id=?
        """,
        (
            dep_id,
        ),
    ).fetchone()


    if not row:

        con.close()

        await q.message.reply_text(
            "❌ Deposit not found."
        )

        return


    if row["status"] != "Pending":

        con.close()

        await q.message.reply_text(
            f"ℹ️ Already handled: "
            f"{row['status']}"
        )

        return


    # -----------------------------------------------------
    # APPROVE
    # -----------------------------------------------------

    if action == "dep_ok":

        con.execute(
            """
            UPDATE deposits
            SET status='Approved',
                reviewed_at=?
            WHERE id=?
            AND status='Pending'
            """,
            (
                now_text(),
                dep_id,
            ),
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

            await q.message.reply_text(
                "❌ Wallet credit failed."
            )

            return


        await q.message.edit_text(
            q.message.text
            + "\n\n"
            f"✅ APPROVED\n"
            f"New balance: ₹{new_bal:.2f}",
            reply_markup=None,
        )


        try:

            await context.bot.send_message(
                row["user_id"],

                "╔══════════════════════╗\n"
                "       ✅ PAYMENT APPROVED\n"
                "╚══════════════════════╝\n\n"

                f"💰 Amount: ₹{row['amount']:.2f}\n"
                f"💵 New Balance: ₹{new_bal:.2f}\n"
                f"🧾 UTR: {row['utr']}"
            )

        except Exception as e:

            print(
                "DEPOSIT USER SEND ERROR:",
                e
            )


    # -----------------------------------------------------
    # REJECT
    # -----------------------------------------------------

    else:

        con.execute(
            """
            UPDATE deposits
            SET status='Rejected',
                reviewed_at=?
            WHERE id=?
            AND status='Pending'
            """,
            (
                now_text(),
                dep_id,
            ),
        )

        con.commit()

        con.close()


        await q.message.edit_text(
            q.message.text
            + "\n\n"
            "❌ REJECTED",
            reply_markup=None,
        )


        try:

            await context.bot.send_message(
                row["user_id"],

                "╔══════════════════════╗\n"
                "       ❌ PAYMENT REJECTED\n"
                "╚══════════════════════╝\n\n"

                f"💰 Amount: ₹{row['amount']:.2f}\n"
                f"🧾 UTR: {row['utr']}\n\n"

                "Agar payment kiya hai to "
                "support se contact karo."
            )

        except Exception as e:

            print(
                "DEPOSIT REJECT SEND ERROR:",
                e
            )


# =========================================================
# ADMIN TEXT STATE
# =========================================================

async def admin_text_state(
    update,
    context
):

    state = context.user_data.get(
        "state"
    )


    if (
        not admin_only(
            update.effective_user.id
        )
        or not state
    ):

        return False


    text = update.message.text.strip()


    # -----------------------------------------------------
    # WALLET LOOKUP
    # -----------------------------------------------------

    if state == "admin_wallet_lookup":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ Numeric user ID bhejo."
            )

            return True


        uid = int(text)

        await admin_wallet_lookup(
            update,
            uid
        )

        clear_state(context)

        return True


    # -----------------------------------------------------
    # ADD / DEDUCT
    # -----------------------------------------------------

    if state in (
        "admin_add_user",
        "admin_deduct_user"
    ):

        parts = text.split()


        if len(parts) != 2:

            await update.message.reply_text(
                "❌ Format:\n"
                "USER_ID AMOUNT"
            )

            return True


        try:

            uid = int(parts[0])

            amount = float(parts[1])

        except ValueError:

            await update.message.reply_text(
                "❌ Invalid values."
            )

            return True


        if amount <= 0:

            await update.message.reply_text(
                "❌ Amount > 0 hona chahiye."
            )

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

            await update.message.reply_text(
                "❌ User nahi mila ya "
                "balance insufficient."
            )

        else:

            await update.message.reply_text(
                "╔══════════════════════╗\n"
                "       ✅ BALANCE UPDATED\n"
                "╚══════════════════════╝\n\n"

                f"👤 User: {uid}\n"
                f"💰 New Balance: ₹{new_bal:.2f}"
            )


            try:

                await context.bot.send_message(
                    uid,

                    f"💰 Wallet update\n\n"
                    f"New balance: ₹{new_bal:.2f}"
                )

            except Exception:
                pass


        return True


    # -----------------------------------------------------
    # REWARD
    # -----------------------------------------------------

    if state == "admin_reward":

        try:

            reward = float(text)

        except ValueError:

            await update.message.reply_text(
                "❌ Number bhejo."
            )

            return True


        if (
            reward < 0
            or reward > 10000
        ):

            await update.message.reply_text(
                "❌ Invalid reward."
            )

            return True


        set_setting(
            "referral_reward",
            reward
        )

        clear_state(context)


        await update.message.reply_text(
            f"✅ Referral reward set:\n"
            f"₹{reward:.2f}"
        )

        return True


    # -----------------------------------------------------
    # BROADCAST
    # -----------------------------------------------------

    if state == "admin_broadcast":

        clear_state(context)


        con = connect()

        users = con.execute(
            """
            SELECT user_id
            FROM users
            """
        ).fetchall()

        con.close()


        sent = 0

        failed = 0


        for row in users:

            try:

                await context.bot.send_message(
                    row["user_id"],
                    text
                )

                sent += 1

            except (
                Forbidden,
                BadRequest
            ):

                failed += 1

            except Exception:

                failed += 1


        await update.message.reply_text(
            "╔══════════════════════╗\n"
            "       📢 BROADCAST DONE\n"
            "╚══════════════════════╝\n\n"

            f"✅ Sent: {sent}\n"
            f"❌ Failed: {failed}"
        )

        return True


    return False


# =========================================================
# ADMIN WALLET LOOKUP
# =========================================================

async def admin_wallet_lookup(
    update,
    uid
):

    con = connect()


    user = con.execute(
        """
        SELECT *
        FROM users
        WHERE user_id=?
        """,
        (
            uid,
        ),
    ).fetchone()


    tx = con.execute(
        """
        SELECT
            kind,
            amount,
            balance_after,
            created_at
        FROM transactions
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 10
        """,
        (
            uid,
        ),
    ).fetchall()


    con.close()


    if not user:

        await update.message.reply_text(
            "❌ User not found."
        )

        return


    text = (
        "╔══════════════════════╗\n"
        "        💰 USER WALLET\n"
        "╚══════════════════════╝\n\n"

        f"🆔 User ID: {uid}\n"
        f"👤 Username: @{user['username'] or '-'}\n"
        f"💰 Balance: ₹{user['balance']:.2f}\n\n"

        "📒 Transactions:\n"
    )


    for r in tx:

        text += (
            f"\n{r['kind']} "
            f"{r['amount']:+.2f}\n"
            f"{fmt_date(r['created_at'])}\n"
        )


    await update.message.reply_text(
        text[:4000]
    )


# =========================================================
# CC ADMIN COMMANDS
# =========================================================

async def ccname_cmd(
    update,
    context
):

    if not admin_only(
        update.effective_user.id
    ):

        return


    value = update.message.text.partition(
        " "
    )[2].strip()


    if not value:

        await update.message.reply_text(
            "Usage: /ccname NAME"
        )

        return


    set_setting(
        "cc_name",
        value
    )


    con = connect()

    con.execute(
        """
        UPDATE cc_items
        SET name=?
        WHERE id=(
            SELECT id
            FROM cc_items
            ORDER BY id
            LIMIT 1
        )
        """,
        (
            value,
        ),
    )

    con.commit()

    con.close()


    await update.message.reply_text(
        "✅ CC name updated."
    )


async def ccprice_cmd(
    update,
    context
):

    if not admin_only(
        update.effective_user.id
    ):

        return


    value = update.message.text.partition(
        " "
    )[2].strip()


    try:

        price = float(value)

    except ValueError:

        await update.message.reply_text(
            "Usage: /ccprice 100"
        )

        return


    if price <= 0:

        await update.message.reply_text(
            "❌ Invalid price."
        )

        return


    set_setting(
        "cc_price",
        price
    )


    con = connect()

    con.execute(
        """
        UPDATE cc_items
        SET price=?
        WHERE id=(
            SELECT id
            FROM cc_items
            ORDER BY id
            LIMIT 1
        )
        """,
        (
            price,
        ),
    )

    con.commit()

    con.close()


    await update.message.reply_text(
        "✅ CC price updated."
    )


async def ccvalue_cmd(
    update,
    context
):

    if not admin_only(
        update.effective_user.id
    ):

        return


    value = update.message.text.partition(
        " "
    )[2].strip()


    if not value:

        await update.message.reply_text(
            "Usage: /ccvalue TEXT"
        )

        return


    set_setting(
        "cc_value",
        value
    )


    con = connect()

    con.execute(
        """
        UPDATE cc_items
        SET value_text=?
        WHERE id=(
            SELECT id
            FROM cc_items
            ORDER BY id
            LIMIT 1
        )
        """,
        (
            value,
        ),
    )

    con.commit()

    con.close()


    await update.message.reply_text(
        "✅ CC value updated."
    )


async def ccdesc_cmd(
    update,
    context
):

    if not admin_only(
        update.effective_user.id
    ):

        return


    value = update.message.text.partition(
        " "
    )[2].strip()


    if not value:

        await update.message.reply_text(
            "Usage: /ccdesc TEXT"
        )

        return


    set_setting(
        "cc_description",
        value
    )


    con = connect()

    con.execute(
        """
        UPDATE cc_items
        SET description=?
        WHERE id=(
            SELECT id
            FROM cc_items
            ORDER BY id
            LIMIT 1
        )
        """,
        (
            value,
        ),
    )

    con.commit()

    con.close()


    await update.message.reply_text(
        "✅ CC description updated."
    )


# =========================================================
# ADD STOCK
# =========================================================

async def addstock_cmd(
    update,
    context
):

    if not admin_only(
        update.effective_user.id
    ):

        return


    code = update.message.text.partition(
        " "
    )[2].strip()


    if not code:

        await update.message.reply_text(
            "Usage:\n"
            "/addstock CODE"
        )

        return


    con = connect()


    item = con.execute(
        """
        SELECT id
        FROM cc_items
        WHERE active=1
        ORDER BY id
        LIMIT 1
        """
    ).fetchone()


    if not item:

        con.close()

        await update.message.reply_text(
            "❌ CC product nahi mila."
        )

        return


    try:

        con.execute(
            """
            INSERT INTO cc_stock
            (
                item_id,
                code,
                status
            )
            VALUES(?,?,'available')
            """,
            (
                item["id"],
                code,
            ),
        )

        con.commit()


        await update.message.reply_text(
            "╔══════════════════════╗\n"
            "        ✅ STOCK ADDED\n"
            "╚══════════════════════╝\n\n"
            f"🔑 Code: {code}"
        )


    except sqlite3.IntegrityError:

        await update.message.reply_text(
            "❌ Ye code already exists."
        )


    finally:

        con.close()


# =========================================================
# CALLBACK ROUTER
# =========================================================

async def callback_router(
    update,
    context
):

    q = update.callback_query

    data = q.data or ""


    if data == "check_join":

        await check_join(
            update,
            context
        )


    elif data.startswith(
        "wallet_"
    ):

        await wallet_callback(
            update,
            context
        )


    elif data.startswith(
        "plan:"
    ):

        await plan_callback(
            update,
            context
        )


    elif (
        data.startswith("like_ok:")
        or data.startswith("like_no:")
    ):

        await like_admin_callback(
            update,
            context
        )


    elif (
        data.startswith("dep_ok:")
        or data.startswith("dep_no:")
    ):

        await deposit_admin_callback(
            update,
            context
        )


    elif data == "cc_buy":

        await cc_buy(
            update,
            context
        )


    elif data.startswith(
        "adm_"
    ):

        await admin_callback(
            update,
            context
        )


    else:

        await q.answer()


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(
    update,
    context
):

    if (
        not update.message
        or not update.effective_user
    ):

        return


    ensure_user(
        update.effective_user
    )


    # Referral verification
    try:

        await process_referral_if_ready(
            context,
            update.effective_user.id
        )

    except Exception as e:

        print(
            "REFERRAL ERROR:",
            e
        )


    # Admin states
    if await admin_text_state(
        update,
        context
    ):

        return


    state = context.user_data.get(
        "state"
    )


    # -----------------------------------------------------
    # USER STATES
    # -----------------------------------------------------

    if state == "deposit_amount":

        await handle_deposit_amount(
            update,
            context
        )

        return


    if state == "deposit_utr":

        await handle_deposit_utr(
            update,
            context
        )

        return


    if state == "like_uid":

        await handle_like_uid(
            update,
            context
        )

        return


    if state == "check_uid":

        await handle_check_uid(
            update,
            context
        )

        return


    # -----------------------------------------------------
    # MAIN MENU
    # -----------------------------------------------------

    text = update.message.text.strip()


    if text == "💰 Wallet":

        await wallet(
            update,
            context
        )


    elif text == "🛒 Buy Like":

        await buy_like(
            update,
            context
        )


    elif text == "📦 My Orders":

        await my_orders(
            update,
            context
        )


    elif text == "🎁 Referral":

        await referral(
            update,
            context
        )


    elif text == "🏪 CC Store":

        await cc_store(
            update,
            context
        )


    elif text == "🆔 Check UID":

        await check_uid_start(
            update,
            context
        )


    elif text == "🛟 Support":

        await support(
            update,
            context
        )


    else:

        await update.message.reply_text(
            "👇 Menu se option choose karo.",
            reply_markup=main_keyboard(),
        )


# =========================================================
# CANCEL
# =========================================================

async def cancel(
    update,
    context
):

    clear_state(context)


    await update.message.reply_text(
        "❌ Current action cancelled.",
        reply_markup=main_keyboard(),
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context
):

    print(
        "BOT ERROR:",
        repr(context.error)
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "Initializing database..."
    )

    init_db()


    # Render web server
    threading.Thread(
        target=run_web,
        daemon=True
    ).start()


    print(
        "Starting Telegram bot..."
    )


    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )


    # -----------------------------------------------------
    # COMMANDS
    # -----------------------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(
        CommandHandler(
            "admin",
            admin_cmd
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
            check_uid_start
        )
    )


    app.add_handler(
        CommandHandler(
            "ccname",
            ccname_cmd
        )
    )


    app.add_handler(
        CommandHandler(
            "ccprice",
            ccprice_cmd
        )
    )


    app.add_handler(
        CommandHandler(
            "ccvalue",
            ccvalue_cmd
        )
    )


    app.add_handler(
        CommandHandler(
            "ccdesc",
            ccdesc_cmd
        )
    )


    app.add_handler(
        CommandHandler(
            "addstock",
            addstock_cmd
        )
    )


    # -----------------------------------------------------
    # CALLBACK
    # -----------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )


    # -----------------------------------------------------
    # TEXT
    # -----------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_router
        )
    )


    # -----------------------------------------------------
    # ERROR
    # -----------------------------------------------------

    app.add_error_handler(
        error_handler
    )


    print(
        "================================="
    )

    print(
        "🔥 VIP BOT STARTED"
    )

    print(
        f"Admin ID: {ADMIN_ID}"
    )

    print(
        f"UID API: {INFO_API}"
    )

    print(
        "================================="
    )


    app.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()