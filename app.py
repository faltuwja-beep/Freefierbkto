import os
import threading
import time
import schedule
from flask import Flask
from pyrogram import Client

app = Flask(__name__)

# Credentials aur session string ab seedha yahan hardcode hain, Maharaj!
API_ID = 33881359
API_HASH = "7f44d8e1ba57e4b58ed3032b94a150d1"
SESSION_STRING = "BQJgio0AUR6cQE-vtauLwAqNoN1_QwvvouqPRbj9CmpmUTuBng6OWrjJtXPsCmQikc0r3O1BhLvYq89O7GKhgEY2iP0AzHj4962-79EJZIt89uhI_-c786Ik6OkgDriTf06TWn3YVdKKgZOKm20ItJzkTuxXBFNc_igeaHtFxH8VJ91tu5r5cWXcx1KKai4-W6_9gYx0Mj38Q-ZDMYrRLX1LITgmHsQRu2UhWo3DyzHpyIaujvSMye1pYgAkWUsX9ikFni_m4BV08xotfVt2nSPYIDpaIBvblJl3gkA998ydk9-EJYAyEoNu10BKPb4IemGRJHtiXLXZH3MU3gPYwdl2Vz2IZwAAAAH5pcL8AA"

TARGET_GROUP = "like_by_paglu"
COMMAND = "/like ind 4232090116"

# Pyrogram Client setup session string ke sath
client = Client(
    "session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

def send_msg():
    print("⏰ Subah ka task shuru ho gaya hai, Maharaj!")
    with client:
        try:
            client.join_chat(TARGET_GROUP)
        except Exception:
            pass
        client.send_message(f"@{TARGET_GROUP}", COMMAND)
        print(f"✅ Success! Command bhej di gayi hai @{TARGET_GROUP} par. 😈🔥")

# Roz subah 6 baje (UTC 00:30 matlab IST subah 6:00 baje)
schedule.every().day.at("00:30").do(send_msg)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

@app.route('/')
def home():
    return "Telegram Auto Bot is Active 24/7, Maharaj! 😈🔥"

if __name__ == "__main__":
    # Background mein schedule chalane ke liye thread
    threading.Thread(target=run_schedule, daemon=True).start()
    
    # Render ke liye Flask web server start karo
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
