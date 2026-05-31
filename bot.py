import asyncio
import os
import uuid
import time
from datetime import datetime
from flask import Flask, request
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from pyrogram.errors import UserNotParticipant, FloodWait
from motor.motor_asyncio import AsyncIOMotorClient

# --- মাস্টার কনফিগারেশন ---
API_ID = 29904834
API_HASH = "8b4fd9ef578af114502feeafa2d31938"
BOT_TOKEN = "8888340548:AAHsGn5TNHF2VxecFWM8_RijY4neyM8iQKI"
MONGO_URL = "mongodb+srv://yeasin018198:yeasin018198@cluster0.eu2cspo.mongodb.net/?appName=Cluster0"

ADMIN_ID = [8932594210] # এখানে আরও আইডি যোগ করতে পারবেন
LOG_CHANNEL = -1003941205520 
FSUB_CHANNEL = -1003990513533 
CHANNEL_LINK = "https://t.me/AllMoviesKings"
ADMIN_USER = "yeasin018198"
AUTO_DELETE_TIME = 600 # ১০ মিনিট পর মেসেজ ডিলিট হবে (সেকেন্ডে)

# ওয়েব হুক ইউআরএল (Render/Koyeb URL)
BASE_URL = "https://movieuplodestore.onrender.com" 

# --- ডাটাবেস সেটআপ ---
client_db = AsyncIOMotorClient(MONGO_URL)
db = client_db["Premium_File_Store"]
files_db = db["files"]
users_db = db["users"]
settings_db = db["settings"]

app = Flask(__name__)
bot = Client("FileStore", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- মেমোরি স্টোরেজ (Temporary States) ---
user_states = {}
maintenance_mode = False

# --- WEBHOOK ROUTE ---
@app.route('/webhook', methods=['POST'])
async def handle_webhook():
    update = Update.de_json(bot, request.get_json())
    await bot.process_update(update)
    return "OK", 200

@app.route('/')
def health_check():
    return "<h1>Bot is running 24/7 with Premium Features</h1>"

# --- সাহায্যকারী ফাংশন (Middleware) ---
async def check_fsub(user_id):
    try:
        await bot.get_chat_member(FSUB_CHANNEL, user_id)
        return True
    except UserNotParticipant:
        return False
    except:
        return True

async def auto_delete_msg(chat_id, message_id):
    await asyncio.sleep(AUTO_DELETE_TIME)
    try:
        await bot.delete_messages(chat_id, message_id)
    except:
        pass

# --- বটের মূল কমান্ডসমূহ ---

@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    user = message.from_user
    
    # ইউজার সেভ করা
    await users_db.update_one({"id": user.id}, {"$set": {"name": user.first_name, "date": datetime.now()}}, upsert=True)

    # মেইনটেন্যান্স মোড চেক
    if maintenance_mode and user.id not in ADMIN_ID:
        return await message.reply_text("🛠 **বট এখন মেইনটেন্যান্স মোডে আছে। পরে চেষ্টা করুন।**")

    # ফোর্স সাবস্ক্রাইব চেক
    if not await check_fsub(user.id):
        btn = [[InlineKeyboardButton("📢 জয়েন করুন", url=CHANNEL_LINK)], [InlineKeyboardButton("🔄 আবার চেষ্টা করুন", url=f"https://t.me/{client.me.username}?start={message.command[1] if len(message.command) > 1 else ''}")]]
        return await message.reply_text("❌ **ফাইল পাওয়ার আগে আমাদের চ্যানেলে জয়েন করুন!**", reply_markup=InlineKeyboardMarkup(btn))

    # যদি লিংক দিয়ে স্টার্ট করে
    if len(message.command) > 1:
        batch_id = message.command[1]
        data = await files_db.find_one({"batch_id": batch_id})
        
        if not data:
            return await message.reply_text("❌ লিংকটি কাজ করছে না।")

        msg_list = []
        status = await message.reply_text("🚀 **ফাইলগুলো পাঠানো হচ্ছে...**")
        
        for index, msg_id in enumerate(data['file_ids'], 1):
            try:
                caption = f"✨ **Name:** `{data['name']}`\n💎 **Part:** `{index:02d}`\n\n📢 {CHANNEL_LINK}"
                m = await client.copy_message(chat_id=user.id, from_chat_id=LOG_CHANNEL, message_id=msg_id, caption=caption)
                msg_list.append(m.id)
                await asyncio.sleep(0.5)
            except FloodWait as e:
                await asyncio.sleep(e.value)
        
        await status.edit(f"✅ **মোট {len(msg_list)}টি ফাইল পাঠানো হয়েছে।**\n\n⚠️ এই ফাইলগুলো ১০ মিনিট পর ডিলিট হয়ে যাবে। দয়া করে অন্য কোথাও সেভ করে রাখুন।")
        
        # অটো ডিলিট টাস্ক
        for m_id in msg_list:
            asyncio.create_task(auto_delete_msg(user.id, m_id))
    else:
        # প্রিমিয়াম ডিজাইন স্টার্ট
        welcome_txt = (
            f"👋 **স্বাগতম, {user.first_name}!**\n\n"
            f"🆔 **আপনার আইডি:** `{user.id}`\n"
            f"🚀 **বট স্ট্যাটাস:** অনলাইন\n\n"
            "ফাইল স্টোর করার জন্য বা লিংক তৈরি করার জন্য এডমিনের সাথে যোগাযোগ করুন।"
        )
        buttons = [[InlineKeyboardButton("📢 মেইন চ্যানেল", url=CHANNEL_LINK)], [InlineKeyboardButton("👨‍💻 এডমিন", url=f"https://t.me/{ADMIN_USER}")]]
        await message.reply_text(welcome_txt, reply_markup=InlineKeyboardMarkup(buttons))

# --- এডমিন প্যানেল ---

@bot.on_message(filters.command("link") & filters.user(ADMIN_ID))
async def make_link(client, message):
    user_states[message.from_user.id] = {"step": "NAME"}
    await message.reply_text("📝 **ফাইলের একটি নাম দিন:**")

@bot.on_message(filters.private & filters.user(ADMIN_ID))
async def admin_input(client, message):
    user_id = message.from_user.id
    if user_id not in user_states: return

    state = user_states[user_id]
    
    if state["step"] == "NAME":
        user_states[user_id] = {"step": "FILES", "name": message.text, "ids": []}
        await message.reply_text("✅ নাম সেভ হয়েছে। এখন ফাইলগুলো পাঠান। শেষ হলে /done লিখুন।")
    
    elif state["step"] == "FILES":
        if message.text == "/done":
            if not state["ids"]: return await message.reply_text("❌ কোনো ফাইল পাঠাননি!")
            
            batch_id = str(uuid.uuid4())[:8]
            await files_db.insert_one({"batch_id": batch_id, "name": state['name'], "file_ids": state['ids']})
            link = f"https://t.me/{client.me.username}?start={batch_id}"
            await message.reply_text(f"✅ **ব্যাচ তৈরি সফল!**\n\n🔗 লিংক: `{link}`")
            del user_states[user_id]
        elif message.media:
            fwd = await message.forward(LOG_CHANNEL)
            user_states[user_id]["ids"].append(fwd.id)

# --- ব্রডকাস্ট ও স্ট্যাটাস ---

@bot.on_message(filters.command("stats") & filters.user(ADMIN_ID))
async def get_stats(client, message):
    total_users = await users_db.count_documents({})
    total_files = await files_db.count_documents({})
    await message.reply_text(f"📊 **বট স্ট্যাটাস:**\n\n👥 মোট ইউজার: {total_users}\n📂 মোট ব্যাচ: {total_files}")

@bot.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast(client, message):
    if not message.reply_to_message: return await message.reply_text("মেসেজ রিপ্লাই দিন।")
    
    users = users_db.find({})
    count = 0
    async for u in users:
        try:
            await message.reply_to_message.copy(u['id'])
            count += 1
            await asyncio.sleep(0.1)
        except: pass
    await message.reply_text(f"✅ ব্রডকাস্ট শেষ! {count} জন ইউজার মেসেজ পেয়েছে।")

# --- রান ফাংশন ---
async def start_bot():
    await bot.start()
    # Webhook setup
    if BASE_URL != "https://your-app.name.onrender.com":
        await bot.set_webhook(f"{BASE_URL}/webhook")
        print("Webhook set successfully!")
    else:
        print("Webhook URL not found. Running with Simple Polling...")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
