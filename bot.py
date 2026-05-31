import os
import asyncio
import uuid
from flask import Flask, request
from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# --- আপনার দেওয়া কনফিগারেশন ---
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

# --- অ্যাসিনক্রোনাস রানার (ভার্সেলের জন্য) ---
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# --- ভার্সেল ওয়েবহোক রুট ---
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
    return "<h1>Bot is Running with Premium Features!</h1>"

# --- বট কমান্ডস ও প্রিমিয়াম ডিজাইন ---

@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    user = message.from_user
    
    # প্রিমিয়াম ডিজাইন বাটন
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Join Main Channel", url=MAIN_CHANNEL_LINK),
            InlineKeyboardButton("👨‍💻 Admin", url=f"https://t.me/{ADMIN_USERNAME}")
        ],
        [
            InlineKeyboardButton("✨ Support Group", url="https://t.me/AllMoviesKings")
        ]
    ])

    if len(message.command) > 1:
        # যদি ইউজার লিংকে ক্লিক করে আসে
        batch_id = message.command[1]
        data = await collection.find_one({"batch_id": batch_id})
        
        if data:
            file_name = data['file_name']
            file_ids = data['file_list']
            status_msg = await message.reply_text(
                f"⚡ **Processing Batch...**\n\n"
                f"📁 **Name:** `{file_name}`\n"
                f"📦 **Total Files:** `{len(file_ids)}`"
            )
            
            count = 0
            for index, msg_id in enumerate(file_ids, 1):
                part_no = f"{index:02d}"
                # আপনার চাহিদা অনুযায়ী কাস্টম ক্যাপশন ডিজাইন
                custom_caption = (
                    f"✨ **Name:** `{file_name}`\n"
                    f"💎 **Part:** `{part_no}`\n\n"
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
                    await asyncio.sleep(0.5) # ফাস্ট কাজের জন্য মিনিমাম গ্যাপ
                except Exception as e:
                    print(f"Error: {e}")
            
            await status_msg.edit(
                f"✅ **Success!**\n\n"
                f"📁 **{file_name}** এর সবগুলো ফাইল চ্যানেলে পাঠানো হয়েছে।\n"
                f"🚀 **Total Sent:** `{count}`",
                reply_markup=buttons
            )
        else:
            await message.reply_text("❌ **Error:** লিংকটি ভ্যালিড নয় অথবা ডাটা ডিলিট করা হয়েছে।")
    else:
        # সাধারণ স্টার্ট মেসেজ (ইউজার ডিটেইলস সহ প্রিমিয়াম লুক)
        start_text = (
            f"👋 **Welcome, {user.first_name}!**\n\n"
            f"🌟 **User Details:**\n"
            f"┣ 📛 **Full Name:** `{user.first_name} {user.last_name if user.last_name else ''}`\n"
            f"┣ 👤 **Username:** @{user.username if user.username else 'None'}\n"
            f"┗ 🆔 **User ID:** `{user.id}`\n\n"
            "🚀 এটি একটি **Premium File Store Bot**। আপনি যদি ফাইল স্টোর করতে চান তবে এডমিনের সাথে যোগাযোগ করুন।"
        )
        await message.reply_text(start_text, reply_markup=buttons)

# --- শুধুমাত্র এডমিন এর জন্য প্রিমিয়াম ফাইল স্টোর লজিক ---

@bot.on_message(filters.command("link") & filters.user(ADMIN_ID))
async def link_cmd(client, message):
    await states.update_one(
        {"user_id": ADMIN_ID}, 
        {"$set": {"state": "WAITING_NAME"}}, 
        upsert=True
    )
    await message.reply_text(
        "📝 **প্রক্রিয়া শুরু হয়েছে!**\n\n"
        "প্রথমে আপনি যে ফাইলগুলো দেবেন তার একটি **নাম** লিখে পাঠান। এটি প্রতিটি ফাইলের ক্যাপশনে থাকবে।"
    )

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
        await message.reply_text(
            f"✅ **নাম সেট করা হয়েছে:** `{file_name}`\n\n"
            f"এখন সিরিয়াল অনুযায়ী ফাইলগুলো পাঠান। সবগুলো ফাইল পাঠানো শেষ হলে নিচের কমান্ডটি দিন:\n\n"
            f"👉 /done"
        )
    
    elif state == "WAITING_FILES":
        if message.media:
            # ফাইল লগ চ্যানেলে ফরোয়ার্ড করা হচ্ছে
            sent_msg = await message.forward(LOG_CHANNEL)
            await states.update_one(
                {"user_id": ADMIN_ID},
                {"$push": {"data.files": sent_msg.id}}
            )
        else:
            await message.reply_text("⚠️ **ভুল ইনপুট!** দয়া করে শুধু ভিডিও বা ফাইল পাঠান।")

@bot.on_message(filters.command("done") & filters.user(ADMIN_ID))
async def done_cmd(client, message):
    user_data = await states.find_one({"user_id": ADMIN_ID})
    
    if user_data and user_data.get("state") == "WAITING_FILES":
        data = user_data.get("data")
        file_list = data.get("files", [])
        
        if not file_list:
            return await message.reply_text("❌ কোনো ফাইল পাওয়া যায়নি! আগে ফাইল পাঠান।")
        
        batch_id = str(uuid.uuid4())[:8]
        await collection.insert_one({
            "batch_id": batch_id,
            "file_name": data['name'],
            "file_list": file_list
        })
        
        # ডাটা রিসেট
        await states.delete_one({"user_id": ADMIN_ID})
        
        bot_info = await client.get_me()
        share_link = f"https://t.me/{bot_info.username}?start={batch_id}"
        
        await message.reply_text(
            f"✨ **Batch Created Successfully!**\n\n"
            f"📂 **Name:** `{data['name']}`\n"
            f"📦 **Files:** `{len(file_list)}`\n\n"
            f"🔗 **Your Link:**\n`{share_link}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Open & Send Files", url=share_link)],
                [InlineKeyboardButton("📢 Main Channel", url=MAIN_CHANNEL_LINK)]
            ])
        )

# ভার্সেল স্টার্টআপ
async def start_bot():
    if not bot.is_connected:
        await bot.start()

run_async(start_bot())
