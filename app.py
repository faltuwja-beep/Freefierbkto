import os
from pyrogram import Client

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

TARGET_GROUP = "like_by_paglu"
COMMAND = "/like ind 4232090116"

app = Client("session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

def main():
    with app:
        try:
            app.join_chat(TARGET_GROUP)
        except Exception:
            pass
        
        app.send_message(f"@{TARGET_GROUP}", COMMAND)
        print(f"✅ Success! Command '{COMMAND}' bhej di gayi hai @{TARGET_GROUP} par. 😈🔥")

if __name__ == "__main__":
    main()
    
