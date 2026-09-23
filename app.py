import os
from pyrogram import Client

# Tere credentials aur session string
API_ID = 33881359
API_HASH = "7f44d8e1ba57e4b58ed3032b94a150d1"
SESSION_STRING = "BQJgio0AUR6cQE-vtauLwAqNoN1_QwvvouqPRbj9CmpmUTuBng6OWrjJtXPsCmQikc0r3O1BhLvYq89O7GKhgEY2iP0AzHj4962-79EJZIt89uhI_-c786Ik6OkgDriTf06TWn3YVdKKgZOKm20ItJzkTuxXBFNc_igeaHtFxH8VJ91tu5r5cWXcx1KKai4-W6_9gYx0Mj38Q-ZDMYrRLX1LITgmHsQRu2UhWo3DyzHpyIaujvSMye1pYgAkWUsX9ikFni_m4BV08xotfVt2nSPYIDpaIBvblJl3gkA998ydk9-EJYAyEoNu10BKPb4IemGRJHtiXLXZH3MU3gPYwdl2Vz2IZwAAAAH5pcL8AA"

TARGET_GROUP = "like_by_paglu"
COMMAND = "/like ind 4232090116"

client = Client(
    "test_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

def test_send():
    print("🚀 Test message bhejne ki koshish ki ja rahi hai, Maharaj...")
    with client:
        try:
            # Group join karne ki koshish karega
            client.join_chat(TARGET_GROUP)
        except Exception:
            pass
        
        # Message bhejega
        client.send_message(f"@{TARGET_GROUP}", COMMAND)
        print(f"✅ Success! Test message bhej diya gaya hai @{TARGET_GROUP} par: {COMMAND} 😈🔥")

if __name__ == "__main__":
    test_send()
    
