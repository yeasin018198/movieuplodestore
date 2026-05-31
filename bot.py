import os
import asyncio
import uuid
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from flask import Flask
from threading import Thread

# --- কনফিগারেশন (আপনার দেওয়া তথ্য অনুযায়ী) ---
API_ID = 29904834
API_HASH = "8b4fd9ef578af114502feeafa2d31938"
BOT_TOKEN = "8888340548:AAHsGn5TNHF2VxecFWM8_RijY4neyM8iQKI"
ADMIN_ID = 8932594210
MONGO_URL = "mongodb+srv://yeasin018198:yeasin018198@cluster0.eu2cspo.mongodb.net/?appName=Cluster0"
LOG_CHANNEL = -1003941205520
USER_CHANNEL = -1003990513533
MAIN_CHANNEL_ID = -1003924710452 
# আপনার চ্যানেলের পাবলিক লিংকটি এখানে দিন
CHANNEL_LINK = "https://t.me/AllMoviesKings" 

# বট ও ডাটাবেস ইনিশিয়ালাইজ
bot = Client("file_store_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client["file_store_db"]
collection = db["files"]
states = db["states"]

# ভার্সেলের জন্য ফ্লস্ক অ্যাপ (বটকে জাগিয়ে রাখতে)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running Fast!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# --- এডমিন ফিল্টার ---
def is_admin(_, __, message):
    return message.from_user and message.from_user.id == ADMIN_ID

# --- কমান্ড হ্যান্ডলার ---

@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    if len(message.command) > 1:
        # যদি লিংকের মাধ্যমে কেউ আসে
        batch_id = message.command[1]
        data = await collection.find_one({"batch_id": batch_id})
        
        if data:
            file_name = data['file_name']
            file_ids = data['file_list']
            status_msg = await message.reply_text(f"🚀 **'{file_name}'** ফাইলগুলো চ্যানেলে পাঠানো হচ্ছে...")
            
            count = 0
            for index, msg_id in enumerate(file_ids, 1):
                part_no = f"{index:02d}"
                # আপনার চাহিদা অনুযায়ী ক্যাপশন
                custom_caption = (
                    f"📂 **Name:** `{file_name}`\n"
                    f"🔹 **Part:** {part_no}\n\n"
                    f"📢 **Join:** {CHANNEL_LINK}"
                )
                
                try:
                    await client.copy_message(
                        chat_id=USER_CHANNEL,
                        from_chat_id=LOG_CHANNEL,
                        message_id=msg_id,
                        caption=custom_caption
                    )
                    count += 1
                    await asyncio.sleep(0.5) # ফাস্ট কাজের জন্য মিনিমাম গ্যাপ
                except Exception as e:
                    print(f"Error sending file: {e}")
            
            await status_msg.edit(f"✅ সফলভাবে **{count}টি** ফাইল চ্যানেলে পাঠানো হয়েছে!")
        else:
            await message.reply_text("❌ ফাইলটি খুঁজে পাওয়া যায়নি বা এটি ডিলিট করা হয়েছে।")
    else:
        # সাধারণ স্টার্ট মেসেজ
        await message.reply_text("স্বাগতম! ফাইল স্টোর করতে চাইলে এডমিন প্যানেলে যোগাযোগ করুন।")

@bot.on_message(filters.command("link") & filters.create(is_admin))
async def link_cmd(client, message):
    await states.update_one(
        {"user_id": ADMIN_ID}, 
        {"$set": {"state": "WAITING_NAME"}}, 
        upsert=True
    )
    await message.reply_text("📝 **ফাইলের নাম দিন:**\n(এই নামটি প্রতিটি ফাইলের ক্যাপশনে থাকবে)")

@bot.on_message(filters.private & filters.create(is_admin) & ~filters.command(["done", "link", "start"]))
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
            # লগ চ্যানেলে ফাইলটি ফরোয়ার্ড করা হচ্ছে
            sent_msg = await message.forward(LOG_CHANNEL)
            await states.update_one(
                {"user_id": ADMIN_ID},
                {"$push": {"data.files": sent_msg.id}}
            )
        else:
            await message.reply_text("⚠️ দয়া করে কোনো ফাইল (Video/File) সেন্ড করুন।")

@bot.on_message(filters.command("done") & filters.create(is_admin))
async def done_cmd(client, message):
    user_data = await states.find_one({"user_id": ADMIN_ID})
    
    if user_data and user_data.get("state") == "WAITING_FILES":
        data = user_data.get("data")
        file_list = data.get("files", [])
        
        if not file_list:
            return await message.reply_text("❌ আপনি কোনো ফাইল দেননি!")
        
        batch_id = str(uuid.uuid4())[:8]
        await collection.insert_one({
            "batch_id": batch_id,
            "file_name": data['name'],
            "file_list": file_list
        })
        
        await states.delete_one({"user_id": ADMIN_ID})
        bot_username = (await client.get_me()).username
        share_link = f"https://t.me/{bot_username}?start={batch_id}"
        
        await message.reply_text(
            f"✅ **লিংক তৈরি হয়েছে!**\n\n📁 নাম: {data['name']}\n📦 ফাইল: {len(file_list)}টি\n\n🔗 লিংক: `{share_link}`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("লিংকটি দেখুন", url=share_link)]])
        )

if __name__ == "__main__":
    # ফ্লস্ক থ্রেড চালু করা
    Thread(target=run_flask).start()
    # বট চালু করা
    bot.run()
