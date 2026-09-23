import os
import threading
import time
import schedule
from flask import Flask
from pyrogram import Client

app = Flask(__name__)

# Credentials
API_ID = int(os.environ.get("API_ID", "33881359"))
API_HASH = os.environ.get("API_HASH", "7f44d8e1ba57e4b58ed3032b94a150d1")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

TARGET_GROUP = "like_by_paglu"
COMMAND = "/like ind 4232090116"

# Pyrogram Client setup
if SESSION_STRING:
    client = Client(
        "session",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=SESSION_STRING,
    )
else:
    client = Client("session", api_id=API_ID, api_hash=API_HASH)


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


@app.route("/")
def home():
  return "Telegram Auto Bot is Active 24/7, Maharaj! 😈🔥"


if __name__ == "__main__":
  # Background mein schedule chalane ke liye thread
  threading.Thread(target=run_schedule, daemon=True).start()

  # Render ke liye Flask web server start karo
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
    
