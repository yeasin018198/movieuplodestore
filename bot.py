import os
import asyncio
import uuid
from flask import Flask, request
from pyrogram import Client, filters, types
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

# বট ও ডাটাবেস ইনিশিয়ালাইজ (Vercel-এর জন্য in_memory=True জরুরি)
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

# --- Webhook হ্যান্ডলিং (Vercel-এর জন্য ১০০% ফিক্সড) ---
@app.route(f"/{BOT_TOKEN}", methods=['POST'])
async def handle_webhook():
    if request.method == "POST":
        update_dict = request.get_json()
        update = types.Update.actual_instance(update_dict)
        
        # বট কানেক্টেড না থাকলে কানেক্ট করা
        if not bot.is_connected:
            await bot.start()
            
        await bot.process_update(update)
        return "OK", 200

@app.route('/')
def index():
    return "Bot is Running Fast and Secure!"

# --- কমান্ড হ্যান্ডলার ---

@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    user = message.from_user
    
    # বাটন সেটআপ
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Main Channel", url=MAIN_CHANNEL_LINK)],
        [InlineKeyboardButton("👨‍💻 Admin Contact", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])

    if len(message.command) > 1:
        # যদি লিংক দিয়ে ফাইল নিতে আসে
        batch_id = message.command[1]
        data = await collection.find_one({"batch_id": batch_id})
        
        if data:
            file_name = data['file_name']
            file_ids = data['file_list']
            status_msg = await message.reply_text(f"🚀 **'{file_name}'** পাঠানো শুরু হচ্ছে...")
            
            count = 0
            for index, msg_id in enumerate(file_ids, 1):
                part_no = f"{index:02d}"
                # আপনার চাহিদা অনুযায়ী ক্যাপশন
                custom_caption = (
                    f"📂 **Name:** `{file_name}`\n"
                    f"🔹 **Part:** {part_no}\n\n"
                    f"📢 **Join:** {MAIN_CHANNEL_LINK}"
                )
                try:
                    # লগ চ্যানেল থেকে ইউজার চ্যানেলে কপি করা
                    await client.copy_message(
                        chat_id=USER_CHANNEL,
                        from_chat_id=LOG_CHANNEL,
                        message_id=msg_id,
                        caption=custom_caption
                    )
                    count += 1
                    await asyncio.sleep(1) # ফাস্ট কাজের জন্য
                except:
                    pass
            
            await status_msg.edit(f"✅ সফলভাবে **{count}টি** ফাইল চ্যানেলে পাঠানো হয়েছে!")
        else:
            await message.reply_text("❌ দুঃখিত! এই লিংকটি কাজ করছে না।")
    else:
        # সাধারণ স্টার্ট মেসেজ (ইউজার ডিটেইলস সহ)
        start_text = (
            f"👋 **স্বাগতম, {user.first_name}!**\n\n"
            f"👤 **নাম:** {user.first_name} {user.last_name if user.last_name else ''}\n"
            f"🆔 **আইডি:** `{user.id}`\n"
            f"🔗 **ইউজারনেম:** @{user.username if user.username else 'None'}\n\n"
            "আপনি এই বটের মাধ্যমে ফাইল স্টোর করতে পারবেন না। স্টোর করতে চাইলে এডমিনের সাথে যোগাযোগ করুন।"
        )
        await message.reply_text(start_text, reply_markup=buttons)

# --- এডমিন কমান্ডস ---

@bot.on_message(filters.command("link") & filters.user(ADMIN_ID))
async def link_cmd(client, message):
    await states.update_one(
        {"user_id": ADMIN_ID}, 
        {"$set": {"state": "WAITING_NAME"}}, 
        upsert=True
    )
    await message.reply_text("📝 **ফাইলের নাম লিখে পাঠান:**")

@bot.on_message(filters.private & filters.user(ADMIN_ID) & ~filters.command(["done", "link", "start"]))
async def handle_admin_input(client, message):
    user_data = await states.find_one({"user_id": ADMIN_ID})
    if not user_data: return

    state = user_data.get("state")
    
    if state == "WAITING_NAME":
        file_name = message.text
        await states.update_one(
            {"user_id": ADMIN_ID}, 
            {"$set": {"state": "WAITING_FILES", "data": {"name": file_name, "files": []}}}
        )
        await message.reply_text(f"✅ নাম সেট হয়েছে: **{file_name}**\n\nএখন সিরিয়াল অনুযায়ী ফাইলগুলো পাঠান। শেষ হলে /done লিখুন।")
    
    elif state == "WAITING_FILES":
        if message.media:
            # লগ চ্যানেলে মেসেজ ফরোয়ার্ড করে আইডি সেভ করা
            sent_msg = await message.forward(LOG_CHANNEL)
            await states.update_one(
                {"user_id": ADMIN_ID},
                {"$push": {"data.files": sent_msg.id}}
            )
        else:
            await message.reply_text("⚠️ দয়া করে কোনো ফাইল বা ভিডিও পাঠান।")

@bot.on_message(filters.command("done") & filters.user(ADMIN_ID))
async def done_cmd(client, message):
    user_data = await states.find_one({"user_id": ADMIN_ID})
    
    if user_data and user_data.get("state") == "WAITING_FILES":
        data = user_data.get("data")
        file_list = data.get("files", [])
        
        if not file_list:
            return await message.reply_text("❌ আপনি কোনো ফাইল পাঠাননি!")
        
        batch_id = str(uuid.uuid4())[:8]
        await collection.insert_one({
            "batch_id": batch_id,
            "file_name": data['name'],
            "file_list": file_list
        })
        
        await states.delete_one({"user_id": ADMIN_ID})
        
        bot_info = await client.get_me()
        share_link = f"https://t.me/{bot_info.username}?start={batch_id}"
        
        await message.reply_text(
            f"✅ **লিংক তৈরি হয়েছে!**\n\n📁 নাম: {data['name']}\n📦 ফাইল: {len(file_list)}টি\n\n🔗 লিংক: `{share_link}`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Link", url=share_link)]])
        )

# ভার্সেলের জন্য বট ইনিশিয়ালাইজ করার জন্য
@app.before_serving
async def startup():
    if not bot.is_connected:
        await bot.start()
