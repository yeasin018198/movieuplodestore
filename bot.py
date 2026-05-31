import os
import asyncio
import uuid
from flask import Flask, request
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# --- কনফিগারেশন (আপনার দেওয়া তথ্য অনুযায়ী) ---
API_ID = 29904834
API_HASH = "8b4fd9ef578af114502feeafa2d31938"
BOT_TOKEN = "8888340548:AAFAp6DegbixhJfoGiioxeC9LW4dulGO2iA"
ADMIN_ID = 8932594210
FILE_CHANNEL = -1003941205520
USER_SEND_CHANNEL = -1003990513533
MONGO_URL = "mongodb+srv://yeasin018198:yeasin018198@cluster0.eu2cspo.mongodb.net/?appName=Cluster0"
WEBHOOK_URL = "https://movieuplodestore.onrender.com"
BOT_URL = "https://t.me/kdramafilestoresBot"
BOT_USERNAME = "kdramafilestoresBot"

# --- ডাটাবেস সেটআপ ---
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client["file_store_database"]
collection = db["file_posts"]

# --- বট এবং ওয়েব সার্ভার সেটআপ ---
app = Client("kdrama_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
web_app = Flask(__name__)

# অ্যাডমিন ডাটা স্টোর করার জন্য
admin_state = {}

# --- ওয়েব রুট (Webhook & Health Check) ---
@web_app.route('/')
def index():
    return "Bot is Running with Webhook!"

@web_app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    # এটি মূলত টেলিগ্রাম থেকে আসা আপডেটগুলো রিসিভ করার জন্য (যদি দরকার হয়)
    return "OK", 200

# --- বটের ফাংশনসমূহ ---

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if len(message.command) > 1:
        post_id = message.command[1]
        post = await collection.find_one({"post_id": post_id})
        
        if post:
            title = post["title"]
            file_ids = post["file_ids"]
            
            await message.reply_text(f"🚀 **আপনার ফাইলগুলো তৈরি হচ্ছে...**\n📂 **নাম:** {title}\n\nএগুলো এখনই `{USER_SEND_CHANNEL}` চ্যানেলে এবং আপনাকে পাঠানো হচ্ছে।")
            
            for index, f_id in enumerate(file_ids, start=1):
                caption = f"🎬 {title}\n\n🔹 **Part {index:02d}**"
                
                # ফাইলটি ইউজারকে সেন্ড করা
                await client.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=FILE_CHANNEL,
                    message_id=f_id,
                    caption=caption
                )
                
                # ফাইলটি ইউজার ফাইল সেন্ড চ্যানেলে পাঠানো
                await client.copy_message(
                    chat_id=USER_SEND_CHANNEL,
                    from_chat_id=FILE_CHANNEL,
                    message_id=f_id,
                    caption=f"{caption}\n\n👤 ইউজার: {message.from_user.mention}"
                )
                await asyncio.sleep(1.5) # রেট লিমিট এড়াতে
        else:
            await message.reply_text("❌ দুঃখিত, এই লিংকটির ফাইল খুঁজে পাওয়া যায়নি।")
    else:
        await message.reply_text(f"স্বাগতম! আমি ফাইল স্টোর বট।\nচ্যানেল লিংক: {BOT_URL}")

@app.on_message(filters.command("post") & filters.user(ADMIN_ID))
async def post_command(client, message):
    admin_state[ADMIN_ID] = {"step": "GET_TITLE", "files": []}
    await message.reply_text("📝 **ফাইলের নাম (Title) দিন:**")

@app.on_message(filters.user(ADMIN_ID) & filters.private)
async def handle_admin_input(client, message):
    state_data = admin_state.get(ADMIN_ID)
    if not state_data:
        return

    if state_data["step"] == "GET_TITLE":
        admin_state[ADMIN_ID]["title"] = message.text
        admin_state[ADMIN_ID]["step"] = "GET_FILES"
        await message.reply_text(f"✅ নাম সেট হয়েছে: **{message.text}**\n\nএখন ফাইলগুলো (Video/Audio/File) একে একে পাঠান। সব পাঠানো শেষ হলে `/done` লিখুন।")

    elif state_data["step"] == "GET_FILES":
        if message.text == "/done":
            if not state_data["files"]:
                await message.reply_text("বসেরা, কোনো ফাইল তো দেননি!")
                return
            
            post_id = str(uuid.uuid4())[:8]
            await collection.insert_one({
                "post_id": post_id,
                "title": state_data["title"],
                "file_ids": state_data["files"]
            })
            
            share_link = f"https://t.me/{BOT_USERNAME}?start={post_id}"
            await message.reply_text(
                f"✅ **সফলভাবে ফাইলগুলো সেভ হয়েছে!**\n\n"
                f"📂 **টাইটেল:** {state_data['title']}\n"
                f"🖇 **আপনার স্টোর লিংক:** `{share_link}`",
                disable_web_page_preview=True
            )
            del admin_state[ADMIN_ID]
            return

        # ফাইলগুলো কপি করে মেইন চ্যানেল (FILE_CHANNEL) এ রাখা হচ্ছে
        if message.media:
            msg = await message.copy(FILE_CHANNEL)
            admin_state[ADMIN_ID]["files"].append(msg.id)
            count = len(admin_state[ADMIN_ID]["files"])
            await message.reply_text(f"📥 ফাইল {count:02d} যোগ হয়েছে। আরও দিলে দিন অথবা `/done` দিন।", quote=True)

# --- রান ফাংশন ---
async def main():
    print("বট স্টার্ট হচ্ছে...")
    await app.start()
    
    # Webhook সেটআপ (আপনার দেওয়া URL ব্যবহার করে)
    webhook_info = await app.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    if webhook_info:
        print(f"Webhook successfully set to {WEBHOOK_URL}")
    
    # ওয়েব সার্ভার ব্যাকগ্রাউন্ডে চালানো
    from threading import Thread
    def run_flask():
        web_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

    Thread(target=run_flask, daemon=True).start()
    
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
