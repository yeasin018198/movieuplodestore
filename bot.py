import os
import asyncio
import uuid
from flask import Flask
from threading import Thread
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# ==================== কনফিগারেশন ====================
API_ID = 29904834
API_HASH = "8b4fd9ef578af114502feeafa2d31938"
BOT_TOKEN = "8888340548:AAFAp6DegbixhJfoGiioxeC9LW4dulGO2iA"
ADMIN_ID = 8932594210
FILE_CHANNEL = -1003941205520
USER_FILE_SEND_CHANNEL = -1003990513533
MONGO_URL = "mongodb+srv://yeasin018198:yeasin018198@cluster0.eu2cspo.mongodb.net/?appName=Cluster0"
BOT_USERNAME = "kdramafilestoresBot"
CHANNEL_INVITE_LINK = "https://t.me/+kGwvviQMj3ZiNjM1"
# ====================================================

# --- ডাটাবেস কানেকশন ---
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client["MovieStoreDB"]
collection = db["posts"]

# --- বট ক্লায়েন্ট ---
app = Client(
    "MovieStoreBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- ওয়েব সার্ভার (Render/Koyeb Keep-Alive) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Running! Webhook is Active."

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# --- অ্যাডমিন স্টেট ম্যানেজমেন্ট ---
admin_data = {}

# --- বটের কমান্ড ও লজিক ---

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    # যদি লিংকের মাধ্যমে আসে (যেমন: /start post_id)
    if len(message.command) > 1:
        post_id = message.command[1]
        post = await collection.find_one({"post_id": post_id})
        
        if post:
            title = post["title"]
            file_ids = post["file_ids"]
            
            # ইউজারকে জানানো হচ্ছে যে কাজ শুরু হয়েছে
            wait_msg = await message.reply_text(f"🎬 **ফাইলের নাম:** {title}\n\nআপনার ফাইলগুলো চ্যানেলে আপলোড করা হচ্ছে, দয়া করে অপেক্ষা করুন...")
            
            first_msg_id = None
            
            for index, file_id in enumerate(file_ids, start=1):
                # সিরিয়াল ক্যাপশন
                caption_text = f"📂 {title}\n📌 Part {index:02d}\n\n👤 ইউজার: {message.from_user.mention}"
                
                try:
                    # ফাইল শুধুমাত্র ইউজার ফাইল সেন্ড চ্যানেলে পাঠানো হচ্ছে (বটে নয়)
                    sent_msg = await client.copy_message(
                        chat_id=USER_FILE_SEND_CHANNEL,
                        from_chat_id=FILE_CHANNEL,
                        message_id=file_id,
                        caption=caption_text
                    )
                    
                    # প্রথম মেসেজের আইডি স্টোর করা হচ্ছে লিংকের জন্য
                    if index == 1:
                        first_msg_id = sent_msg.id
                    
                    await asyncio.sleep(1.5) # ফ্লাড কন্ট্রোল
                except Exception as e:
                    print(f"Error sending file: {e}")

            # ফাইল পাঠানো শেষ হলে ইউজারকে বাটন সহ মেসেজ আপডেট দেওয়া
            if first_msg_id:
                # প্রাইভেট চ্যানেল মেসেজ লিংকের ফরম্যাট তৈরি
                channel_id_str = str(USER_FILE_SEND_CHANNEL).replace("-100", "")
                post_link = f"https://t.me/c/{channel_id_str}/{first_msg_id}"
                
                buttons = [
                    [InlineKeyboardButton("📂 চ্যানেলে দেখুন", url=CHANNEL_INVITE_LINK)],
                    [InlineKeyboardButton("🚀 সরাসরি প্রথম ফাইলে যান", url=post_link)]
                ]
                
                await wait_msg.edit_text(
                    f"✅ **আপনার ফাইলগুলো তৈরি!**\n\n"
                    f"আপনার অনুরোধ করা ফাইলগুলো নিচের চ্যানেলে আপলোড করা হয়েছে। কপিরাইট এড়াতে সরাসরি বটে ফাইল দেওয়া হয় না।\n\n"
                    f"🎬 **টাইটেল:** {title}\n\n"
                    f"নিচের বাটনে ক্লিক করে ফাইলগুলো সংগ্রহ করুন।",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
        else:
            await message.reply_text("❌ দুঃখিত! এই লিংকটি ডাটাবেসে পাওয়া যায়নি।")
    else:
        # সাধারণ স্টার্ট মেসেজ
        await message.reply_text(
            f"স্বাগতম {message.from_user.mention}!\n\n"
            f"আমি একটি ফাইল স্টোর বট। আপনি মুভি বা ড্রামার লিংকে ক্লিক করলে আমি সেই ফাইলগুলো আমাদের মেইন চ্যানেলে পাঠিয়ে দিবো।"
        )

# /post কমান্ড (শুধুমাত্র অ্যাডমিনের জন্য)
@app.on_message(filters.command("post") & filters.user(ADMIN_ID) & filters.private)
async def post_init(client, message):
    admin_data[ADMIN_ID] = {"step": "TITLE", "files": []}
    await message.reply_text("📝 অনুগ্রহ করে ফাইলের নাম (Title) লিখুন:")

# অ্যাডমিন ইনপুট হ্যান্ডেলার
@app.on_message(filters.user(ADMIN_ID) & filters.private)
async def admin_input_handler(client, message):
    if ADMIN_ID not in admin_data:
        return

    # যদি কমান্ড হয় তবে এটি হ্যান্ডেল করবে না (বটে কমান্ড কনফ্লিক্ট এড়াতে)
    if message.text and message.text.startswith("/"):
        if message.text == "/done":
            pass # নিচে হ্যান্ডেল করা হয়েছে
        else:
            return

    user_step = admin_data[ADMIN_ID]["step"]

    # ১. নাম গ্রহণ করা
    if user_step == "TITLE":
        admin_data[ADMIN_ID]["title"] = message.text
        admin_data[ADMIN_ID]["step"] = "FILES"
        await message.reply_text(f"✅ টাইটেল সেট হয়েছে: **{message.text}**\n\nএখন ফাইলগুলো (Video, Audio, Document) একে একে পাঠান। সব পাঠানো শেষ হলে `/done` কমান্ড দিন।")

    # ২. ফাইল গ্রহণ করা
    elif user_step == "FILES":
        if message.text == "/done":
            if not admin_data[ADMIN_ID]["files"]:
                await message.reply_text("⚠️ আপনি কোনো ফাইল আপলোড করেননি! অন্তত একটি ফাইল দিন।")
                return
            
            # ডাটাবেসে সেভ করা
            post_unique_id = str(uuid.uuid4())[:8]
            final_title = admin_data[ADMIN_ID]["title"]
            all_files = admin_data[ADMIN_ID]["files"]

            await collection.insert_one({
                "post_id": post_unique_id,
                "title": final_title,
                "file_ids": all_files
            })

            share_link = f"https://t.me/{BOT_USERNAME}?start={post_unique_id}"
            
            await message.reply_text(
                f"✅ **সফলভাবে সেভ হয়েছে!**\n\n"
                f"📂 নাম: {final_title}\n"
                f"🔢 মোট ফাইল: {len(all_files)}\n\n"
                f"🔗 আপনার শেয়ারিং লিংক: `{share_link}`",
                disable_web_page_preview=True
            )
            # স্টেট ক্লিয়ার
            del admin_data[ADMIN_ID]
            return

        # অ্যাডমিনের পাঠানো ফাইল ফাইল চ্যানেলে কপি করা
        if message.media:
            try:
                stored_msg = await message.copy(FILE_CHANNEL)
                admin_data[ADMIN_ID]["files"].append(stored_msg.id)
                count = len(admin_data[ADMIN_ID]["files"])
                await message.reply_text(f"📥 ফাইল {count:02d} যোগ হয়েছে। আরও থাকলে দিন অথবা `/done` লিখুন।", quote=True)
            except Exception as e:
                await message.reply_text(f"❌ এরর: {e}")

# --- রান ফাংশন ---
async def start_bot():
    print("--------------------------")
    print("বট স্টার্ট হচ্ছে...")
    await app.start()
    print("বট সফলভাবে চালু হয়েছে!")
    print("--------------------------")
    
    # ওয়েব সার্ভার থ্রেড
    web_thread = Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    await idle()
    await app.stop()

if __name__ == "__main__":
    # বট রান করা
    try:
        app.run(start_bot())
    except KeyboardInterrupt:
        pass
