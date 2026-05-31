import os
import asyncio
import uuid
from flask import Flask, request
from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# --- কনফিগারেশন (আপনার দেওয়া তথ্য) ---
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
app = Flask(__name__)
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

# --- হেল্পার ফাংশন (সিঙ্ক্রোনাস থেকে অ্যাসিনক্রোনাস চালানোর জন্য) ---
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# --- ভার্সেল ওয়েবহোক রুট (ইরোর ফিক্সড) ---
@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def handle_webhook():
    if request.method == "POST":
        update_dict = request.get_json()
        update = types.Update.actual_instance(update_dict)
        
        async def process():
            if not bot.is_connected:
                await bot.start()
            await bot.process_update(update)
            
        run_async(process())
        return "OK", 200

@app.route('/')
def index():
    return "Bot is Running Securely!"

# --- কমান্ড হ্যান্ডলার ---

@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    user = message.from_user
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Main Channel", url=MAIN_CHANNEL_LINK)],
        [InlineKeyboardButton("👨‍💻 Admin Contact", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])

    if len(message.command) > 1:
        batch_id = message.command[1]
        data = await collection.find_one({"batch_id": batch_id})
        
        if data:
            file_name = data['file_name']
            file_ids = data['file_list']
            status_msg = await message.reply_text(f"🚀 **'{file_name}'** পাঠানো শুরু হচ্ছে...")
            
            count = 0
            for index, msg_id in enumerate(file_ids, 1):
                part_no = f"{index:02d}"
                custom_caption = (
                    f"📂 **Name:** `{file_name}`\n"
                    f"🔹 **Part:** {part_no}\n\n"
                    f"📢 **Join:** {MAIN_CHANNEL_LINK}"
                )
                try:
                    await client.copy_message(
                        chat_id=USER_CHANNEL,
                        from_chat_id=LOG_CHANNEL,
                        message_id=msg_id,
                        caption=custom_caption
                    )
                    count += 1
                    await asyncio.sleep(1)
                except: pass
            await status_msg.edit(f"✅ সফলভাবে **{count}টি** ফাইল চ্যানেলে দেওয়া হয়েছে!")
        else:
            await message.reply_text("❌ ডাটা পাওয়া যায়নি।")
    else:
        start_text = (
            f"👋 **Hello, {user.first_name}!**\n\n"
            f"👤 **Name:** {user.first_name} {user.last_name if user.last_name else ''}\n"
            f"🆔 **ID:** `{user.id}`\n"
            f"🔗 **Username:** @{user.username if user.username else 'None'}\n\n"
            "বটটি সচল আছে।"
        )
        await message.reply_text(start_text, reply_markup=buttons)

@bot.on_message(filters.command("link") & filters.user(ADMIN_ID))
async def link_cmd(client, message):
    await states.update_one({"user_id": ADMIN_ID}, {"$set": {"state": "WAITING_NAME"}}, upsert=True)
    await message.reply_text("📝 **ফাইলের নাম দিন:**")

@bot.on_message(filters.private & filters.user(ADMIN_ID) & ~filters.command(["done", "link", "start"]))
async def handle_admin_input(client, message):
    user_data = await states.find_one({"user_id": ADMIN_ID})
    if not user_data: return
    state = user_data.get("state")
    
    if state == "WAITING_NAME":
        await states.update_one({"user_id": ADMIN_ID}, {"$set": {"state": "WAITING_FILES", "data": {"name": message.text, "files": []}}})
        await message.reply_text(f"✅ নাম: **{message.text}**\nএখন সিরিয়াল বাই সিরিয়াল ফাইল পাঠান, শেষে /done লিখুন।")
    
    elif state == "WAITING_FILES" and message.media:
        sent_msg = await message.forward(LOG_CHANNEL)
        await states.update_one({"user_id": ADMIN_ID}, {"$push": {"data.files": sent_msg.id}})

@bot.on_message(filters.command("done") & filters.user(ADMIN_ID))
async def done_cmd(client, message):
    user_data = await states.find_one({"user_id": ADMIN_ID})
    if user_data and user_data.get("state") == "WAITING_FILES":
        data = user_data.get("data")
        batch_id = str(uuid.uuid4())[:8]
        await collection.insert_one({"batch_id": batch_id, "file_name": data['name'], "file_list": data['files']})
        await states.delete_one({"user_id": ADMIN_ID})
        bot_me = await client.get_me()
        link = f"https://t.me/{bot_me.username}?start={batch_id}"
        await message.reply_text(f"✅ **লিংক:** `{link}`")
