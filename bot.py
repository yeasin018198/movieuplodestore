import os
import asyncio
import uuid
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# --- কনফিগারেশন ---
API_ID = 29904834
API_HASH = "8b4fd9ef578af114502feeafa2d31938"
BOT_TOKEN = "8888340548:AAHsGn5TNHF2VxecFWM8_RijY4neyM8iQKI"
ADMIN_ID = 8932594210
MONGO_URL = "mongodb+srv://yeasin018198:yeasin018198@cluster0.eu2cspo.mongodb.net/?appName=Cluster0"
LOG_CHANNEL = -1003941205520
USER_CHANNEL = -1003990513533
MAIN_CHANNEL_LINK = "https://t.me/AllMoviesKings"
ADMIN_USERNAME = "yeasin018198"

# বট ও ডাটাবেস ইনিশিয়ালাইজ
bot = Client(
    "file_store_bot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN, 
    in_memory=True
)

db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client["file_store_db"]
collection = db["files"]
states = db["states"]

# --- Flask সার্ভার (Render/Koyeb Health Check এর জন্য) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running 24/7!"

def run_flask():
    # Render/Koyeb সাধারণত 8080 বা 10000 পোর্টে রান করতে বলে
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- বটের কমান্ড ও লজিক ---

@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    user = message.from_user
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Join Main Channel", url=MAIN_CHANNEL_LINK),
            InlineKeyboardButton("👨‍💻 Admin", url=f"https://t.me/{ADMIN_USERNAME}")
        ],
        [InlineKeyboardButton("✨ Support Group", url="https://t.me/AllMoviesKings")]
    ])

    if len(message.command) > 1:
        batch_id = message.command[1]
        data = await collection.find_one({"batch_id": batch_id})
        
        if data:
            file_name = data['file_name']
            file_ids = data['file_list']
            status_msg = await message.reply_text(f"⚡ **Processing Batch...**\n\n📁 **Name:** `{file_name}`")
            
            count = 0
            for index, msg_id in enumerate(file_ids, 1):
                custom_caption = (
                    f"✨ **Name:** `{file_name}`\n"
                    f"💎 **Part:** `{index:02d}`\n\n"
                    f"🚀 **Fast Uploaded by File Store Bot**\n"
                    f"📢 **Join Our Channel:** {MAIN_CHANNEL_LINK}"
                )
                try:
                    await client.copy_message(
                        chat_id=USER_CHANNEL,
                        from_chat_id=LOG_CHANNEL,
                        message_id=msg_id,
                        caption=custom_caption
                    )
                    count += 1
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"Error sending file: {e}")
            
            await status_msg.edit(
                f"✅ **Success!**\n\n📁 **{file_name}** এর ফাইল পাঠানো হয়েছে।\n🚀 **Total Sent:** `{count}`",
                reply_markup=buttons
            )
        else:
            await message.reply_text("❌ **Error:** ডাটা পাওয়া যায়নি।")
    else:
        start_text = (
            f"👋 **Welcome, {user.first_name}!**\n\n"
            f"🌟 **User Details:**\n"
            f"┣ 📛 **Name:** `{user.first_name}`\n"
            f"┗ 🆔 **User ID:** `{user.id}`\n\n"
            "🚀 এটি একটি **Premium File Store Bot**।"
        )
        await message.reply_text(start_text, reply_markup=buttons)

@bot.on_message(filters.command("link") & filters.user(ADMIN_ID))
async def link_cmd(client, message):
    await states.update_one({"user_id": ADMIN_ID}, {"$set": {"state": "WAITING_NAME"}}, upsert=True)
    await message.reply_text("📝 **প্রক্রিয়া শুরু হয়েছে!**\nপ্রথমে ফাইলের **নাম** লিখে পাঠান।")

@bot.on_message(filters.private & filters.user(ADMIN_ID) & ~filters.command(["done", "link", "start"]))
async def handle_admin_input(client, message):
    user_data = await states.find_one({"user_id": ADMIN_ID})
    if not user_data: return
    state = user_data.get("state")
    
    if state == "WAITING_NAME":
        file_name = message.text
        await states.update_one({"user_id": ADMIN_ID}, {"$set": {"state": "WAITING_FILES", "data": {"name": file_name, "files": []}}})
        await message.reply_text(f"✅ **নাম সেট:** `{file_name}`\nএখন সব ফাইল পাঠান, শেষে /done লিখুন।")
    
    elif state == "WAITING_FILES":
        if message.media:
            sent_msg = await message.forward(LOG_CHANNEL)
            await states.update_one({"user_id": ADMIN_ID}, {"$push": {"data.files": sent_msg.id}})
        else:
            await message.reply_text("⚠️ শুধু ভিডিও বা ফাইল পাঠান।")

@bot.on_message(filters.command("done") & filters.user(ADMIN_ID))
async def done_cmd(client, message):
    user_data = await states.find_one({"user_id": ADMIN_ID})
    if user_data and user_data.get("state") == "WAITING_FILES":
        data = user_data.get("data")
        file_list = data.get("files", [])
        if not file_list: return await message.reply_text("❌ ফাইল পাঠাননি!")
        
        batch_id = str(uuid.uuid4())[:8]
        await collection.insert_one({"batch_id": batch_id, "file_name": data['name'], "file_list": file_list})
        await states.delete_one({"user_id": ADMIN_ID})
        
        bot_info = await client.get_me()
        share_link = f"https://t.me/{bot_info.username}?start={batch_id}"
        await message.reply_text(f"✨ **Batch Created!**\n\n🔗 **Link:** `{share_link}`")

# --- রান করার মেইন ফাংশন ---
if __name__ == "__main__":
    # Flask সার্ভার আলাদা থ্রেডে চালানো (Health Check এর জন্য)
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    print("Bot is starting via Polling...")
    bot.run()
