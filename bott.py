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
            "🎁 Demo Pack",
            1,
            1,
            5
        ),

        (
            "starter",
            "🚀 Starter Pack",
            220,
            15,
            59
        ),

        (
            "pro",
            "💎 Pro Master Pack",
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
        return "N/A"

    try:

        dt = datetime.fromisoformat(value)

        return dt.astimezone().strftime(
            "%d-%m-%Y | %I:%M %p"
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
                "💰 My Wallet",
                "🛒 Buy Likes"
            ],
            [
                "📦 My Orders",
                "🎁 Referral Zone"
            ],
            [
                "🏪 CC Store",
                "🆔 Check UID"
            ],
            [
                "🛟 Support Center"
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
                    "👥 Users List",
                    callback_data="adm_users"
                ),
            ],

            [
                InlineKeyboardButton(
                    "💰 User Wallet Lookup",
                    callback_data="adm_wallet"
                ),

                InlineKeyboardButton(
                    "➕ Add Balance",
                    callback_data="adm_add"
                ),
            ],

            [
                InlineKeyboardButton(
                    "➖ Deduct Balance",
                    callback_data="adm_deduct"
                ),

                InlineKeyboardButton(
                    "📒 All Transactions",
                    callback_data="adm_tx"
                ),
            ],

            [
                InlineKeyboardButton(
                    "💳 Pending UTRs",
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
                    "🏪 CC Store Config",
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
                    "📢 Broadcast Message",
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
                "✅ Verify & Continue",
                callback_data="check_join"
            )
        ]
    )


    await update.effective_message.reply_text(
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "     📢 **MANDATORY CHANNELS**     \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        "⚠️ Bot ke saare features use karne ke liye niche diye gaye channels ko join karna zaroori hai!\n\n"
        "👇 Join karne ke baad button dabayein:",
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
        parse_mode="Markdown"
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
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "       🔥 **VIP GAMING HUB** 🔥       \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"👋 Welcome, **{user.first_name or 'Gamer'}**!\n\n"
        f"💰 **Wallet Balance:** `₹{balance(user.id):.2f}`\n\n"
        "⚡ Yahan aapko milta hai sabse fast aur secure gaming automation service.\n\n"
        "👇 Apni pasand ka option niche se select karein:",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
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

        await q.message.edit_text(
            "✨ **VERIFICATION SUCCESSFUL!** ✨\n\n"
            "Ab aap bot ka poora maza le sakte hain. Menu niche active ho gaya hai.",
            reply_markup=None
        )
        
        await q.message.reply_text(
            "🚀 Main Menu:",
            reply_markup=main_keyboard()
        )

    else:

        await q.answer(
            "❌ Aapne sabhi channels join nahi kiye hain!",
            show_alert=True
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
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "          💰 **YOUR WALLET**          \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"💵 **Current Balance:** `₹{balance(uid):.2f}`\n\n"
        "💡 Balance add karne ke liye niche click karein ya apne transactions check karein.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ Add Money to Wallet",
                        callback_data="wallet_add"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📒 View Transaction History",
                        callback_data="wallet_tx"
                    )
                ],
            ]
        ),
        parse_mode="Markdown"
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


        await q.message.edit_text(
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "       ➕ **ADD MONEY SYSTEM**       \n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"💳 **Official UPI ID:**\n`{UPI_ID}`\n\n"
            "📌 **Instructions:**\n"
            "1. Upar di gayi UPI ID par payment karein.\n"
            "2. Jitna amount add karna hai wo yahan bhej dein (Example: `100`).",
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

            await q.message.edit_text(
                "📒 Aapka transaction history abhi khaali hai."
            )

            return


        lines = [
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
            "     📒 **TRANSACTION LOGS**     ",
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n",
        ]


        for r in rows:

            sign = (
                "+"
                if r["amount"] >= 0
                else ""
            )

            lines.append(
                f"🔹 **{r['kind']}**\n"
                f"   Amount: `{sign}₹{r['amount']:.2f}`\n"
                f"   Balance After: `₹{r['balance_after']:.2f}`\n"
                f"   🕒 `{fmt_date(r['created_at'])}`\n"
            )


        await q.message.edit_text(
            "\n".join(lines),
            parse_mode="Markdown"
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
            "❌ Kripya ek valid amount dalein (Jaise: `100`)",
            parse_mode="Markdown"
        )

        return


    if (
        amount < 1
        or amount > 100000
    ):

        await update.message.reply_text(
            "❌ Amount ₹1 se ₹1,00,000 ke beech hi hona chahiye."
        )

        return


    context.user_data[
        "deposit_amount_value"
    ] = amount

    context.user_data[
        "state"
    ] = "deposit_utr"


    await update.message.reply_text(
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "       💳 **PAYMENT VERIFICATION**    \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"💰 **Selected Amount:** `₹{amount:.2f}`\n\n"
        f"🎯 **Pay to UPI:**\n`{UPI_ID}`\n\n"
        "✨ Payment karne ke baad uska **UTR / Transaction ID** yahan type karke bhej dein.",
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
            "❌ Kripya sahi UTR/Transaction ID bhejein."
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
            "❌ Session expire ho gaya hai. Kripya dubara try karein."
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
            "❌ Ye UTR pehle hi submit kiya ja chuka hai!"
        )

        return


    finally:

        try:
            con.close()
        except Exception:
            pass


    clear_state(context)


    await update.message.reply_text(
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "       ✅ **UTR SUBMITTED**         \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"💰 **Amount:** `₹{amount:.2f}`\n"
        f"🧾 **UTR:** `{utr}`\n"
        f"🆔 **Deposit ID:** `{dep_id}`\n\n"
        "⏳ Admin dwara verification ke turant baad aapka balance update kar diya jayega.",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )


    try:

        await context.bot.send_message(
            ADMIN_ID,

            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "       🔔 **NEW UTR SUBMISSION**   \n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"🆔 **ID:** `{dep_id}`\n"
            f"👤 **User ID:** `{update.effective_user.id}`\n"
            f"🌐 **Username:** @{update.effective_user.username or 'none'}\n"
            f"💰 **Amount:** `₹{amount:.2f}`\n"
            f"🧾 **UTR:** `{utr}`",

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

        print("ADMIN UTR SEND ERROR:", e)


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
                    f"{p['name']} — ₹{p['price']}",
                    callback_data=f"plan:{p['code']}"
                )
            ]
        )


    await update.message.reply_text(
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "       ❤️ **FREE FIRE LIKE PLANS**    \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        "👇 Apni zaroorat ke hisaab se best plan select karein:\n\n"
        "💡 *Note:* Payment aapke wallet se automatically cut ho jayegi.",

        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
        parse_mode="Markdown"
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

        await q.message.edit_text(
            "❌ Yeh plan abhi available nahi hai."
        )

        return


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

            await q.message.edit_text(
                "⏳ Aapne pichle 24 ghante mein pehle hi Demo use kar liya hai!"
            )

            return


    current_balance = balance(
        q.from_user.id
    )


    if current_balance < float(
        p["price"]
    ):

        await q.message.edit_text(
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "       ❌ **LOW BALANCE**         \n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"💰 **Required:** `₹{p['price']:.2f}`\n"
            f"💵 **Your Balance:** `₹{current_balance:.2f}`\n\n"
            "👇 Kripya wallet mein balance add karein.",
            parse_mode="Markdown"
        )

        return


    context.user_data[
        "state"
    ] = "like_uid"


    context.user_data[
        "plan_code"
    ] = code


    await q.message.edit_text(
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "       🎯 **ENTER YOUR UID**        \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"📦 **Plan:** {p['name']}\n"
        f"💰 **Price:** `₹{p['price']:.2f}`\n\n"
        "🎮 Kripya apna sahi **Free Fire UID** niche bhejhein:",
        parse_mode="Markdown"
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
            "❌ Kripya ek valid numeric Free Fire UID dalein."
        )

        return


    code = context.user_data.get(
        "plan_code"
    )


    if not code:

        clear_state(context)

        await update.message.reply_text(
            "❌ Session expire ho gaya. Dubara try karein."
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
            "❌ Plan invalid hai."
        )

        return


    price = float(
        p["price"]
    )


    ok, new_balance = change_balance(
        update.effective_user.id,
        -price,
        "Like order reserve",
        "pending-order",
    )


    if not ok:

        clear_state(context)

        await update.message.reply_text(
            "❌ Wallet balance kam pad gaya."
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

        change_balance(
            update.effective_user.id,
            price,
            "Order creation refund",
            order_id,
        )

        clear_state(context)

        await update.message.reply_text(
            "❌ Order place nahi ho saka. Amount refund kar diya gaya hai."
        )

        return


    con.close()

    clear_state(context)


    await update.message.reply_text(
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "       ✅ **ORDER PLACED**          \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"🆔 **Order ID:** `{order_id}`\n"
        f"🎮 **Target UID:** `{uid}`\n"
        f"💰 **Amount Paid:** `₹{price:.2f}`\n"
        "📌 **Status:** `Pending Approval`\n\n"
        "🚀 Admin approval ke baad likes process hone lagenge.",

        parse_mode="Markdown",

        reply_markup=main_keyboard(),
    )


    try:

        await context.bot.send_message(
            ADMIN_ID,

            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "       ❤️ **NEW LIKE ORDER**        \n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"🆔 **Order:** `{order_id}`\n"
            f"👤 **User:** `{update.effective_user.id}` (@{update.effective_user.username or 'none'})\n"
            f"📦 **Plan:** {p['name']}\n"
            f"🎮 **UID:** `{uid}`\n"
            f"💰 **Amount:** `₹{price:.2f}`",

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

        print("ADMIN LIKE SEND ERROR:", e)


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
            "❌ Order nahi mila."
        )

        return


    if row["status"] != "Pending Approval":

        con.close()

        await q.message.reply_text(
            f"ℹ️ Yeh order pehle hi handle ho chuka hai: {row['status']}"
        )

        return


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
            "✅ **STATUS:** `APPROVED & ACTIVE`",
            reply_markup=None,
            parse_mode="Markdown"
        )


        try:

            await context.bot.send_message(
                row["user_id"],

                "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
                "       🚀 **ORDER APPROVED**        \n"
                "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
                f"🆔 **Order ID:** `{order_id}`\n"
                f"🎮 **UID:** `{row['uid']}`\n"
                "📌 **Status:** `Active / Processing`",
                parse_mode="Markdown"
            )

        except Exception as e:

            print("USER APPROVE SEND ERROR:", e)


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
            "❌ **STATUS:** `REJECTED & REFUNDED`",
            reply_markup=None,
            parse_mode="Markdown"
        )


        try:

            await context.bot.send_message(
                row["user_id"],

                "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
                "       ❌ **ORDER REJECTED**        \n"
                "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
                f"🆔 **Order ID:** `{order_id}`\n"
                f"💰 **Refunded:** `₹{row['amount']:.2f}`\n\n"
                "Amount aapke wallet mein wapas bhej diya gaya hai.",
                parse_mode="Markdown"
            )

        except Exception as e:

            print("USER REFUND SEND ERROR:", e)


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
            "📦 Aapne abhi tak koi order nahi banaya hai.",
            reply_markup=main_keyboard(),
        )

        return


    lines = [
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
        "        📦 **YOUR ORDERS**         ",
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n",
    ]


    for r in rows:

        lines.append(
            f"🆔 `{r['id']}`\n"
            f"📦 Plan: **{r['name'] or r['plan_code']}**\n"
            f"🎮 UID: `{r['uid']}`\n"
            f"💰 Paid: `₹{r['amount']:.2f}`\n"
            f"📌 Status: `{r['status']}`\n"
            f"🕒 Date: `{fmt_date(r['approved_at'])}`\n"
            "----------------------------"
        )


    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
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
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "       🎁 **REFERRAL PROGRAM**      \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        "🔗 **Aapka Referral Link:**\n"
        f"`{link}`\n\n"
        f"💸 **Per Invite Reward:** `₹{reward:.2f}`\n"
        f"👥 **Total Friends Invited:** `{len(rows)}`\n"
        f"✅ **Successful Referrals:** `{paid}`\n\n"
        "📢 Apne dosto ke sath share karein aur free balance kamayein!",

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
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "        🛟 **SUPPORT DESK**        \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"👨‍💻 **Admin Support:** {SUPPORT_USERNAME}\n\n"
        "Agar aapko payment, order ya kisi bhi cheez mein problem aaye toh seedhe contact karein.",

        reply_markup=main_keyboard(),
        parse_mode="Markdown"
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
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "         🆔 **CHECK UID**           \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        "🎮 Kripya jis Free Fire player ki info nikalni hai uska **UID** bhejein:\n\n"
        "Example:\n`14307670967`",

        parse_mode="Markdown",
    )


# =========================================================
# FIXED UID API HANDLER
# =========================================================

async def handle_check_uid(
    update,
    context
):

    uid = update.message.text.strip()


    if not uid.isdigit() or not (5 <= len(uid) <= 15):

        await update.message.reply_text(
            "❌ **Invalid UID!** Kripya sirf sahi numbers wala Free Fire UID bhejein.",
            parse_mode="Markdown"
        )

        return


    status_message = await update.message.reply_text(
        "🔎 **Fetching player details...**\n⏳ Kripya thoda intezaar karein...",
        parse_mode="Markdown"
    )


    try:

        response = requests.get(
            INFO_API,
            params={
                "uid": uid,
                "key": INFO_API_KEY,
            },
            timeout=25,
        )

        if response.status_code != 200:
            await status_message.edit_text("❌ API server se connect karne mein problem aayi hai. Kuch der baad try karein.")
            return

        data = response.json()

    except Exception as e:
        print("UID API ERROR:", e)
        await status_message.edit_text("❌ UID fetch karte samay error aaya hai. API key ya endpoint check karein.")
        return


    if not isinstance(data, dict):
        await status_message.edit_text("❌ API se galat format mila hai.")
        return


    # Safe data extraction with fallbacks
    basic = data.get("basicInfo") or data.get("basic_info") or {}
    social = data.get("socialInfo") or data.get("social_info") or {}
    pet = data.get("petInfo") or data.get("pet_info") or {}
    clan = data.get("clanBasicInfo") or data.get("clan_basic_info") or {}
    credit = data.get("creditScoreInfo") or {}

    nickname = basic.get("nickname") or basic.get("name") or "Unknown"
    region = basic.get("region") or basic.get("server") or "Unknown"
    level = basic.get("level") or "N/A"
    exp = basic.get("exp") or "N/A"
    rank = basic.get("rank") or "N/A"
    cs_rank = basic.get("csRank") or basic.get("cs_rank") or "N/A"
    max_rank = basic.get("maxRank") or basic.get("max_rank") or "N/A"
    liked = basic.get("liked") or basic.get("likes") or 0
    account_type = basic.get("accountType") or "N/A"
    release_version = basic.get("releaseVersion") or "N/A"

    ranking_points = basic.get("rankingPoints") or "N/A"
    clan_name = clan.get("clanName") or clan.get("name") or "No Clan"
    clan_id = clan.get("clanId") or clan.get("id") or "N/A"
    pet_id = pet.get("id") or "N/A"
    language = social.get("language") or "N/A"
    signature = social.get("signature") or "No signature"
    credit_score = credit.get("creditScore") or "N/A"


    result = (
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "       🎮 **FREE FIRE PROFILE**      \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"👤 **Name:** `{nickname}`\n"
        f"🆔 **UID:** `{uid}`\n"
        f"🌍 **Region:** `{region}`\n\n"
        "📊 **-- ACCOUNT STATS --**\n"
        f"⭐ **Level:** `{level}` (EXP: {exp})\n"
        f"🏆 **BR Rank:** `{rank}`\n"
        f"⚔️ **CS Rank:** `{cs_rank}`\n"
        f"🏅 **Max Rank:** `{max_rank}`\n"
        f"❤️ **Likes:** `{liked}`\n"
        f"💯 **Credit Score:** `{credit_score}`\n\n"
        "👥 **-- GUILD / CLAN --**\n"
        f"🏷️ **Name:** `{clan_name}`\n"
        f"🆔 **ID:** `{clan_id}`\n\n"
        "🌐 **-- OTHER INFO --**\n"
        f"📝 **Signature:** `{signature}`\n"
        f"📱 **App Version:** `{release_version}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 **VIP Gaming Bot Engine**"
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
        price = float(item["price"])
        value = item["value_text"]
        desc = item["description"]

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

        name = get_setting("cc_name", "Digital Code")
        price = float(get_setting("cc_price", "100"))
        value = get_setting("cc_value", "₹3,000 Value")
        desc = get_setting("cc_description", "")
        stock = 0


    con.close()


    await update.message.reply_text(
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "        🏪 **DIGITAL CC STORE**      \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"📦 **Product:** {name}\n"
        f"💰 **Price:** `₹{price:.2f}`\n"
        f"🎁 **Value:** {value}\n"
        f"📦 **Available Stock:** `{stock}`\n\n"
        f"📝 **Details:** {desc}\n",

        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🛒 Buy Now Instantly",
                        callback_data="cc_buy"
                    )
                ]
            ]
        ),
        parse_mode="Markdown"
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

        await q.message.edit_text("❌ Product available nahi hai.")

        return


    price = float(
        item["price"]
    )


    try:

        con.execute("BEGIN IMMEDIATE")

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

            await q.message.edit_text("❌ Sorry, abhi stock khatam ho gaya hai!")

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


        if not user or float(user["balance"]) < price:

            con.rollback()
            con.close()

            current = balance(q.from_user.id)

            await q.message.edit_text(
                "❌ **Low Balance!**\n\n"
                f"Required: `₹{price:.2f}`\n"
                f"Your Balance: `₹{current:.2f}`",
                parse_mode="Markdown"
            )

            return


        new_balance = float(user["balance"]) - price


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

        print("CC SALE ERROR:", e)
        con.rollback()
        con.close()

        await q.message.edit_text("❌ Purchase process fail ho gaya.")

        return


    con.close()


    await q.message.edit_text(
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "      ✅ **PURCHASE SUCCESSFUL**    \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"📦 **Product:** {item['name']}\n"
        f"💰 **Amount Paid:** `₹{price:.2f}`\n\n"
        "🔑 **Aapka Code:**\n"
        f"`{stock['code']}`\n\n"
        "⚠️ Is code ko securely save karke rakhein!",

        parse_mode="Markdown",
    )


# =========================================================
# ADMIN
# =========================================================

def admin_only(user_id):
    return user_id == ADMIN_ID


async def admin_cmd(update, context):

    if not admin_only(update.effective_user.id):
        await update.message.reply_text("❌ Aap admin nahi hain.")
        return

    clear_state(context)

    await update.message.reply_text(
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "        🛠 **ADMIN CONTROL PANEL**   \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        "Select an action below:",
        reply_markup=admin_keyboard(),
        parse_mode="Markdown"
    )


async def admin_callback(update, context):

    q = update.callback_query
    await q.answer()

    if not admin_only(q.from_user.id):
        return

    action = q.data

    if action == "adm_dashboard":

        con = connect()
        users = con.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        pending_utr = con.execute("SELECT COUNT(*) c FROM deposits WHERE status='Pending'").fetchone()["c"]
        pending_likes = con.execute("SELECT COUNT(*) c FROM orders WHERE status='Pending Approval'").fetchone()["c"]
        total_balance = con.execute("SELECT COALESCE(SUM(balance),0) s FROM users").fetchone()["s"]
        total_deposits = con.execute("SELECT COALESCE(SUM(amount),0) s FROM deposits WHERE status='Approved'").fetchone()["s"]
        total_orders = con.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"]
        con.close()

        await q.message.reply_text(
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "        📊 **ADMIN DASHBOARD**      \n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"👥 Total Users: `{users}`\n"
            f"💰 User Wallets Total: `₹{float(total_balance):.2f}`\n"
            f"💳 Approved Deposits: `₹{float(total_deposits):.2f}`\n"
            f"📦 Total Orders: `{total_orders}`\n"
            f"⏳ Pending UTRs: `{pending_utr}`\n"
            f"❤️ Pending Likes: `{pending_likes}`",
            parse_mode="Markdown"
        )

    elif action == "adm_users":

        con = connect()
        rows = con.execute("SELECT user_id, username, first_name, balance FROM users ORDER BY created_at DESC LIMIT 25").fetchall()
        con.close()

        if not rows:
            await q.message.reply_text("No users found.")
            return

        text = ["┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n        👥 **RECENT USERS**\n┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n"]
        for r in rows:
            text.append(f"🆔 `{r['user_id']}` | @{r['username'] or '-'} | `₹{r['balance']:.2f}`")

        await q.message.reply_text("\n".join(text)[:4000], parse_mode="Markdown")

    elif action == "adm_wallet":
        context.user_data["state"] = "admin_wallet_lookup"
        await q.message.reply_text("💰 Jiska balance check karna hai uski Telegram ID bhejein:")

    elif action == "adm_add":
        context.user_data["state"] = "admin_add_user"
        await q.message.reply_text("➕ **Add Balance Format:**\n`USER_ID AMOUNT`\n\nExample:\n`123456789 100`", parse_mode="Markdown")

    elif action == "adm_deduct":
        context.user_data["state"] = "admin_deduct_user"
        await q.message.reply_text("➖ **Deduct Balance Format:**\n`USER_ID AMOUNT`\n\nExample:\n`123456789 50`", parse_mode="Markdown")

    elif action == "adm_tx":
        con = connect()
        rows = con.execute("SELECT user_id, kind, amount, balance_after FROM transactions ORDER BY id DESC LIMIT 25").fetchall()
        con.close()
        text = ["┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n        📒 **TRANSACTIONS**\n┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n"]
        for r in rows:
            text.append(f"`{r['user_id']}` | {r['kind']} | `{r['amount']:+.2f}` | `₹{r['balance_after']:.2f}`")
        await q.message.reply_text("\n".join(text)[:4000], parse_mode="Markdown")

    elif action == "adm_utr":
        con = connect()
        rows = con.execute("SELECT * FROM deposits WHERE status='Pending' ORDER BY created_at ASC LIMIT 15").fetchall()
        con.close()

        if not rows:
            await q.message.reply_text("✅ Koi pending UTR nahi hai.")
            return

        for r in rows:
            await q.message.reply_text(
                "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
                "        💳 **PENDING UTR**          \n"
                "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
                f"🆔 ID: `{r['id']}`\n"
                f"👤 User: `{r['user_id']}`\n"
                f"💰 Amount: `₹{r['amount']:.2f}`\n"
                f"🧾 UTR: `{r['utr']}`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("✅ Approve", callback_data=f"dep_ok:{r['id']}"),
                            InlineKeyboardButton("❌ Reject", callback_data=f"dep_no:{r['id']}"),
                        ]
                    ]
                ),
            )

    elif action == "adm_likes":
        con = connect()
        rows = con.execute("SELECT o.*, p.name FROM orders o LEFT JOIN plans p ON p.code=o.plan_code WHERE o.status='Pending Approval' ORDER BY o.created_at ASC LIMIT 15").fetchall()
        con.close()

        if not rows:
            await q.message.reply_text("✅ Koi pending like order nahi hai.")
            return

        for r in rows:
            await q.message.reply_text(
                "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
                "       ❤️ **PENDING LIKE ORDER**    \n"
                "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
                f"🆔 Order: `{r['id']}`\n"
                f"👤 User: `{r['user_id']}`\n"
                f"📦 Plan: {r['name'] or r['plan_code']}\n"
                f"🎮 UID: `{r['uid']}`\n"
                f"💰 Amount: `₹{r['amount']:.2f}`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("✅ Approve", callback_data=f"like_ok:{r['id']}"),
                            InlineKeyboardButton("❌ Reject", callback_data=f"like_no:{r['id']}"),
                        ]
                    ]
                ),
            )

    elif action == "adm_orders":
        con = connect()
        rows = con.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 25").fetchall()
        con.close()
        text = ["┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n        📦 **ALL ORDERS**\n┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n"]
        for r in rows:
            text.append(f"`{r['id']}` | U:{r['user_id']} | UID:{r['uid']} | {r['status']}")
        await q.message.reply_text("\n".join(text)[:4000], parse_mode="Markdown")

    elif action == "adm_refs":
        con = connect()
        rows = con.execute("SELECT * FROM referrals ORDER BY id DESC LIMIT 25").fetchall()
        con.close()
        text = ["┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n        🎁 **REFERRALS**\n┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n"]
        for r in rows:
            text.append(f"`{r['referrer_id']}` → `{r['referred_id']}` | {r['status']} | `₹{r['reward']:.2f}`")
        await q.message.reply_text("\n".join(text)[:4000], parse_mode="Markdown")

    elif action == "adm_reward":
        context.user_data["state"] = "admin_reward"
        await q.message.reply_text(f"Current Reward: `₹{float(get_setting('referral_reward','2')):.2f}`\n\nNaya reward amount bhejein:", parse_mode="Markdown")

    elif action == "adm_broadcast":
        context.user_data["state"] = "admin_broadcast"
        await q.message.reply_text("📢 Sabhi users ko bhejne ke liye message type karein:")

    elif action == "adm_cc":
        await q.message.reply_text(
            "Commands to configure CC store:\n"
            "/ccname NAME\n"
            "/ccprice AMOUNT\n"
            "/ccvalue TEXT\n"
            "/ccdesc TEXT"
        )

    elif action == "adm_stock":
        con = connect()
        item = con.execute("SELECT id FROM cc_items WHERE active=1 ORDER BY id LIMIT 1").fetchone()
        count = con.execute("SELECT COUNT(*) c FROM cc_stock WHERE item_id=? AND status='available'", (item["id"],)).fetchone()["c"] if item else 0
        con.close()
        await q.message.reply_text(f"📦 Available Codes in Stock: `{count}`\n\nStock add karne ke liye command use karein:\n`/addstock CODE`", parse_mode="Markdown")


async def deposit_admin_callback(update, context):

    q = update.callback_query
    await q.answer()

    if not admin_only(q.from_user.id):
        return

    action, dep_id = q.data.split(":", 1)
    con = connect()
    row = con.execute("SELECT * FROM deposits WHERE id=?", (dep_id,)).fetchone()

    if not row:
        con.close()
        await q.message.reply_text("❌ Deposit nahi mila.")
        return

    if row["status"] != "Pending":
        con.close()
        await q.message.reply_text(f"ℹ️ Yeh pehle hi process ho chuka hai: {row['status']}")
        return

    if action == "dep_ok":
        con.execute("UPDATE deposits SET status='Approved', reviewed_at=? WHERE id=? AND status='Pending'", (now_text(), dep_id))
        con.commit()
        con.close()

        ok, new_bal = change_balance(row["user_id"], float(row["amount"]), "UPI deposit", dep_id)

        if not ok:
            await q.message.reply_text("❌ Wallet credit fail ho gaya.")
            return

        await q.message.edit_text(q.message.text + f"\n\n✅ **APPROVED**\nNew Balance: `₹{new_bal:.2f}`", parse_mode="Markdown")

        try:
            await context.bot.send_message(
                row["user_id"],
                "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
                "       ✅ **PAYMENT APPROVED**      \n"
                "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
                f"💰 Amount Added: `₹{row['amount']:.2f}`\n"
                f"💵 New Balance: `₹{new_bal:.2f}`\n"
                f"🧾 UTR: `{row['utr']}`",
                parse_mode="Markdown"
            )
        except Exception as e:
            print("DEPOSIT USER SEND ERROR:", e)

    else:
        con.execute("UPDATE deposits SET status='Rejected', reviewed_at=? WHERE id=? AND status='Pending'", (now_text(), dep_id))
        con.commit()
        con.close()

        await q.message.edit_text(q.message.text + "\n\n❌ **REJECTED**", parse_mode="Markdown")

        try:
            await context.bot.send_message(
                row["user_id"],
                "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
                "       ❌ **PAYMENT REJECTED**      \n"
                "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
                f"💰 Amount: `₹{row['amount']:.2f}`\n"
                f"🧾 UTR: `{row['utr']}`\n\n"
                "Agar koi dikkat hai toh support se contact karein.",
                parse_mode="Markdown"
            )
        except Exception as e:
            print("DEPOSIT REJECT SEND ERROR:", e)


async def admin_text_state(update, context):

    state = context.user_data.get("state")

    if not admin_only(update.effective_user.id) or not state:
        return False

    text = update.message.text.strip()

    if state == "admin_wallet_lookup":
        if not text.isdigit():
            await update.message.reply_text("❌ Sahi numeric user ID dalein.")
            return True
        uid = int(text)
        await admin_wallet_lookup(update, uid)
        clear_state(context)
        return True

    if state in ("admin_add_user", "admin_deduct_user"):
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ Format:\n`USER_ID AMOUNT`", parse_mode="Markdown")
            return True
        try:
            uid = int(parts[0])
            amount = float(parts[1])
        except ValueError:
            await update.message.reply_text("❌ Galat values di gayi hain.")
            return True

        if amount <= 0:
            await update.message.reply_text("❌ Amount 0 se zyada hona chahiye.")
            return True

        if state == "admin_deduct_user":
            amount = -amount

        ok, new_bal = change_balance(uid, amount, "Admin balance update", f"admin:{update.effective_user.id}")
        clear_state(context)

        if not ok:
            await update.message.reply_text("❌ User nahi mila ya balance insufficient hai.")
        else:
            await update.message.reply_text(
                "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
                "       ✅ **BALANCE UPDATED**      \n"
                "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
                f"👤 User ID: `{uid}`\n"
                f"💰 New Balance: `₹{new_bal:.2f}`",
                parse_mode="Markdown"
            )
            try:
                await context.bot.send_message(uid, f"💰 Aapka wallet update kar diya gaya hai.\nNew Balance: `₹{new_bal:.2f}`", parse_mode="Markdown")
            except Exception:
                pass
        return True

    if state == "admin_reward":
        try:
            reward = float(text)
        except ValueError:
            await update.message.reply_text("❌ Kripya number dalein.")
            return True

        set_setting("referral_reward", reward)
        clear_state(context)
        await update.message.reply_text(f"✅ Referral reward successfully set ho gaya hai: `₹{reward:.2f}`", parse_mode="Markdown")
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
            except Exception:
                failed += 1

        await update.message.reply_text(
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "       📢 **BROADCAST DONE**        \n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"✅ Sent: `{sent}`\n"
            f"❌ Failed: `{failed}`",
            parse_mode="Markdown"
        )
        return True

    return False


async def admin_wallet_lookup(update, uid):
    con = connect()
    user = con.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    tx = con.execute("SELECT kind, amount, balance_after, created_at FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 10", (uid,)).fetchall()
    con.close()

    if not user:
        await update.message.reply_text("❌ User database mein nahi mila.")
        return

    text = (
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "        💰 **USER DETAILS**         \n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"🆔 ID: `{uid}`\n"
        f"👤 Username: @{user['username'] or '-'}\n"
        f"💰 Balance: `₹{user['balance']:.2f}`\n\n"
        "📒 **Last Transactions:**\n"
    )

    for r in tx:
        text += f"• {r['kind']} | `{r['amount']:+.2f}` (`{fmt_date(r['created_at'])}`)\n"

    await update.message.reply_text(text[:4000], parse_mode="Markdown")


# =========================================================
# CC ADMIN COMMANDS
# =========================================================

async def ccname_cmd(update, context):
    if not admin_only(update.effective_user.id):
        return
    val = update.message.text.partition(" ")[2].strip()
    if not val:
        await update.message.reply_text("Usage: /ccname NAME")
        return
    set_setting("cc_name", val)
    con = connect()
    con.execute("UPDATE cc_items SET name=? WHERE id=(SELECT id FROM cc_items ORDER BY id LIMIT 1)", (val,))
    con.commit()
    con.close()
    await update.message.reply_text("✅ CC name updated.")

async def ccprice_cmd(update, context):
    if not admin_only(update.effective_user.id):
        return
    val = update.message.text.partition(" ")[2].strip()
    try:
        price = float(val)
    except ValueError:
        await update.message.reply_text("Usage: /ccprice 100")
        return
    set_setting("cc_price", price)
    con = connect()
    con.execute("UPDATE cc_items SET price=? WHERE id=(SELECT id FROM cc_items ORDER BY id LIMIT 1)", (price,))
    con.commit()
    con.close()
    await update.message.reply_text("✅ CC price updated.")

async def ccvalue_cmd(update, context):
    if not admin_only(update.effective_user.id):
        return
    val = update.message.text.partition(" ")[2].strip()
    if not val:
        await update.message.reply_text("Usage: /ccvalue TEXT")
        return
    set_setting("cc_value", val)
    con = connect()
    con.execute("UPDATE cc_items SET value_text=? WHERE id=(SELECT id FROM cc_items ORDER BY id LIMIT 1)", (val,))
    con.commit()
    con.close()
    await update.message.reply_text("✅ CC value text updated.")

async def ccdesc_cmd(update, context):
    if not admin_only(update.effective_user.id):
        return
    val = update.message.text.partition(" ")[2].strip()
    if not val:
        await update.message.reply_text("Usage: /ccdesc TEXT")
        return
    set_setting("cc_description", val)
    con = connect()
    con.execute("UPDATE cc_items SET description=? WHERE id=(SELECT id FROM cc_items ORDER BY id LIMIT 1)", (val,))
    con.commit()
    con.close()
    await update.message.reply_text("✅ CC description updated.")

async def addstock_cmd(update, context):
    if not admin_only(update.effective_user.id):
        return
    code = update.message.text.partition(" ")[2].strip()
    if not code:
        await update.message.reply_text("Usage: /addstock CODE")
        return

    con = connect()
    item = con.execute("SELECT id FROM cc_items WHERE active=1 ORDER BY id LIMIT 1").fetchone()
    if not item:
        con.close()
        await update.message.reply_text("❌ CC product available nahi hai.")
        return

    try:
        con.execute("INSERT INTO cc_stock (item_id, code, status) VALUES (?,?,'available')", (item["id"], code))
        con.commit()
        await update.message.reply_text(f"✅ Stock code added successfully:\n`{code}`", parse_mode="Markdown")
    except sqlite3.IntegrityError:
        await update.message.reply_text("❌ Yeh code pehle se stock mein mojood hai!")
    finally:
        con.close()


# =========================================================
# ROUTERS
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


async def text_router(update, context):
    if not update.message or not update.effective_user:
        return

    ensure_user(update.effective_user)

    try:
        await process_referral_if_ready(context, update.effective_user.id)
    except Exception as e:
        print("REFERRAL ERROR:", e)

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

    if text == "💰 My Wallet":
        await wallet(update, context)
    elif text == "🛒 Buy Likes":
        await buy_like(update, context)
    elif text == "📦 My Orders":
        await my_orders(update, context)
    elif text == "🎁 Referral Zone":
        await referral(update, context)
    elif text == "🏪 CC Store":
        await cc_store(update, context)
    elif text == "🆔 Check UID":
        await check_uid_start(update, context)
    elif text == "🛟 Support Center":
        await support(update, context)
    else:
        await update.message.reply_text(
            "👇 Kripya niche diye gaye menu se koi option select karein:",
            reply_markup=main_keyboard(),
        )


async def cancel(update, context):
    clear_state(context)
    await update.message.reply_text("❌ Current action cancel kar diya gaya hai.", reply_markup=main_keyboard())


async def error_handler(update, context):
    print("BOT ERROR:", repr(context.error))


# =========================================================
# MAIN
# =========================================================

def main():
    print("Initializing database...")
    init_db()

    threading.Thread(target=run_web, daemon=True).start()

    print("Starting Telegram bot...")

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
    app.add_error_handler(error_handler)

    print("=================================")
    print("🔥 VIP BOT STARTED SUCCESSFULLY")
    print(f"Admin ID: {ADMIN_ID}")
    print("=================================")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
