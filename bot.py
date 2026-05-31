import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from flask import Flask
from threading import Thread

# --- কনফিগারেশন ---
API_ID = 29904834
API_HASH = "8b4fd9ef578af114502feeafa2d31938"
BOT_TOKEN = "8888340548:AAFAp6DegbixhJfoGiioxeC9LW4dulGO2iA"
ADMIN_ID = 8932594210
FILE_CHANNEL = -1003941205520
USER_SEND_CHANNEL = -1003990513533
MONGO_URL = "mongodb+srv://yeasin018198:yeasin018198@cluster0.eu2cspo.mongodb.net/?appName=Cluster0"
BOT_USERNAME = "kdramafilestoresBot"

# --- ডাটাবেস সেটআপ ---
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client["file_store_bot"]
collection = db["posts"]

# --- বট ক্লায়েন্ট ---
app = Client("file_store_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# অ্যাডমিনের স্টেট ট্র্যাক করার জন্য
user_data = {}

# --- ওয়েব সার্ভার (Render/Koyeb এর জন্য) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Running!"

def run_web():
    web_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- বটের ফাংশনসমূহ ---

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    if len(message.command) > 1:
        # যদি লিংকের মাধ্যমে কেউ আসে
        post_id = message.command[1]
        post = await collection.find_one({"post_id": post_id})
        
        if post:
            files = post["file_ids"]
            title = post["title"]
            await message.reply_text(f"**ফাইলের নাম:** {title}\n\nফাইলগুলো পাঠানো হচ্ছে...")
            
            for index, file_id in enumerate(files, start=1):
                caption = f"{title} - Part {index:02d}"
                # ফাইলগুলো ইউজার চ্যানেল বা ইউজারকে পাঠানো
                await client.copy_message(
                    chat_id=message.chat.id, 
                    from_chat_id=FILE_CHANNEL, 
                    message_id=file_id,
                    caption=caption
                )
                await asyncio.sleep(1) # ফ্লাড কন্ট্রোল
        else:
            await message.reply_text("দুঃখিত, এই ফাইলটি খুঁজে পাওয়া যায়নি।")
    else:
        await message.reply_text("হ্যালো! আমি একটি ফাইল স্টোর বট। মুভি বা ফাইল পেতে সঠিক লিংকে ক্লিক করুন।")

@app.on_message(filters.command("post") & filters.user(ADMIN_ID))
async def post_init(client, message):
    user_data[ADMIN_ID] = {"step": "TITLE", "files": []}
    await message.reply_text("অনুগ্রহ করে ফাইলের জন্য একটি নাম (Title) দিন।")

@app.on_message(filters.user(ADMIN_ID))
async def handle_admin_input(client, message):
    if ADMIN_ID not in user_data:
        return

    state = user_data[ADMIN_ID]["step"]

    if state == "TITLE":
        user_data[ADMIN_ID]["title"] = message.text
        user_data[ADMIN_ID]["step"] = "FILES"
        await message.reply_text(f"টাইটেল সেট হয়েছে: **{message.text}**\n\nএখন ফাইলগুলো একটা একটা করে সেন্ড করুন। শেষ হলে /done কমান্ড দিন।")

    elif state == "FILES":
        if message.text == "/done":
            if not user_data[ADMIN_ID]["files"]:
                await message.reply_text("আপনি কোনো ফাইল দেননি!")
                return
            
            # ডাটাবেসে সেভ করা
            import uuid
            post_id = str(uuid.uuid4())[:8]
            title = user_data[ADMIN_ID]["title"]
            file_ids = user_data[ADMIN_ID]["files"]

            await collection.insert_one({
                "post_id": post_id,
                "title": title,
                "file_ids": file_ids
            })

            link = f"https://t.me/{BOT_USERNAME}?start={post_id}"
            await message.reply_text(f"✅ পোস্ট সফলভাবে সম্পন্ন হয়েছে!\n\n**টাইটেল:** {title}\n**মোট ফাইল:** {len(file_ids)}\n\n**আপনার লিংক:** {link}")
            del user_data[ADMIN_ID]
            return

        # ফাইল স্টোর করা (Video, Audio, Document, Photo)
        if message.media:
            msg = await message.copy(FILE_CHANNEL)
            user_data[ADMIN_ID]["files"].append(msg.id)
            await message.reply_text(f"ফাইল যোগ করা হয়েছে (Part {len(user_data[ADMIN_ID]['files']):02d})। আরও ফাইল থাকলে দিন অথবা /done লিখুন।", quote=True)

# বট চালু করা
if __name__ == "__main__":
    Thread(target=run_web).start()
    print("বট স্টার্ট হচ্ছে...")
    app.run()
