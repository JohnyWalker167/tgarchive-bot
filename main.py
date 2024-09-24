import uuid
from utils import *
from config import *
from tmdb import get_by_url, get_by_name
from html import escape
from time import time as tm
from pyrogram import idle
from pyromod import listen
from pyrogram.errors import FloodWait
from pyrogram import Client, filters, enums
from shorterner import *
from asyncio import get_event_loop
from pymongo import MongoClient
from pyrogram.types import User
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

loop = get_event_loop()

MONGO_COLLECTION = "users"
mongo_client = MongoClient(MONGO_URL)
mongo_db = mongo_client[MONGO_DB_NAME]
mongo_collection = mongo_db[MONGO_COLLECTION]

user_data = {}
TOKEN_TIMEOUT = 28800

app = Client(
    "my_bot",
      api_id=API_ID,
      api_hash=API_HASH, 
      bot_token=BOT_TOKEN, 
      workers=1000, 
      parse_mode=enums.ParseMode.HTML
      )


async def main():
    async with app:
        await idle()

with app:
    bot_username = (app.get_me()).username

@app.on_message(filters.private & filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    user_link = await get_user_link(message.from_user)

    if len(message.command) > 1 and message.command[1] == "token":
        try:
            file_id = 1563
            get_msg = await app.get_messages(DB_CHANNEL_ID, int(file_id))
            cpy_msg = await get_msg.copy(chat_id=message.chat.id)
            await message.delete()
            await asyncio.sleep(300)
            await cpy_msg.delete()
            return
            
        except Exception as e:
            logger.error(f"{e}")
        return

    if len(message.command) > 1 and message.command[1].startswith("token_"):
        input_token = message.command[1][6:]
        token_msg = await verify_token(user_id, input_token)
        reply = await message.reply_text(token_msg)
        await app.send_message(LOG_CHANNEL_ID, f"User🕵️‍♂️{user_link} with 🆔 {user_id} @{bot_username} {token_msg}", parse_mode=enums.ParseMode.HTML)
        await auto_delete_message(message, reply)
        return

    file_id = message.command[1] if len(message.command) > 1 else None

    if file_id:
        if not await check_access(message, user_id):
            return
        try:
            file_message = await app.get_messages(DB_CHANNEL_ID, int(file_id))
            media = file_message.video or file_message.audio or file_message.document
            if media:
                caption = file_message.caption if file_message.caption else None
                if caption:
                    new_caption = await remove_extension(caption)
                    copy_message = await file_message.copy(chat_id=message.chat.id, caption=f"<b>{new_caption}</b>", parse_mode=enums.ParseMode.HTML)
                    user_data[user_id]['file_count'] = user_data[user_id].get('file_count', 0) + 1
                else:
                    copy_message = await file_message.copy(chat_id=message.chat.id)
                    user_data[user_id]['file_count'] = user_data[user_id].get('file_count', 0) + 1
                await auto_delete_message(message, copy_message)
                await asyncio.sleep(3)
            else:
                reply = await message.reply_text("File not found or inaccessible.")
                await auto_delete_message(message, reply)

        except ValueError:
            reply = await message.reply_text("Invalid File ID") 
            await auto_delete_message(message, reply)  

        except FloodWait as f:
            await asyncio.sleep(f.value)
            if caption:
                copy_message = await file_message.copy(chat_id=message.chat.id, caption=f"<b>{new_caption}</b>", parse_mode=enums.ParseMode.HTML)
                user_data[user_id]['file_count'] = user_data[user_id].get('file_count', 0) + 1
            else:
                copy_message = await file_message.copy(chat_id=message.chat.id)
                user_data[user_id]['file_count'] = user_data[user_id].get('file_count', 0) + 1

            await auto_delete_message(message, copy_message)
            await asyncio.sleep(3)
    
    else:
        mongo_collection.update_one(
                {'user_id': user_id},
                {'$set': {'user_id': user_id}}, 
                upsert=True
            )                   
        reply = await message.reply_text(f"<b>💐Welcome this is TG⚡️Flix Bot")
        await auto_delete_message(message, reply)

@app.on_message(filters.private & (filters.document | filters.video| filters.photo) & filters.user(OWNER_USERNAME))
async def forward_message_to_new_channel(client, message):
    photo = 'photo.jpg'
    media = message.document or message.video
    
    if media:
        try:
            caption = message.caption if message.caption else None
            file_size = media.file_size if media.file_size else None

            if caption:
                new_caption = await remove_unwanted(caption)
                cap_no_ext = await remove_extension(new_caption)
                movie_name, release_year = await extract_movie_info(cap_no_ext)
                poster_url = await get_movie_poster(movie_name, release_year)
                
                cpy_msg = await message.copy(DB_CHANNEL_ID, caption=f"<code>{escape(new_caption)}</code>", parse_mode=enums.ParseMode.HTML)
                await message.delete()

                file_info = f"🗂️ <b>{escape(cap_no_ext)}</b>\n\n💾 <b>{humanbytes(file_size)}</b>"
                file_link  = f"https://thetgflix.sshemw.workers.dev/bot1/{cpy_msg.id}"

                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Get File", url=file_link)]])

                if poster_url:
                    # Send the message with the TMDb poster
                    await app.send_photo(CAPTION_CHANNEL_ID, poster_url, caption=file_info, reply_markup=keyboard)
                else:
                    # If no movie details, fallback to default poster and caption
                    await app.send_photo(CAPTION_CHANNEL_ID, photo, caption=file_info, reply_markup=keyboard)

        except Exception as e:
            logger.error(f'{e}')
            # Fallback in case of any error
            await app.send_photo(CAPTION_CHANNEL_ID, photo, caption=file_info, reply_markup=keyboard)
            await asyncio.sleep(3)

    if message.photo:
        await message.copy(CAPTION_CHANNEL_ID)
        await message.delete()
        

@app.on_message(filters.private & filters.command("send") & filters.user(OWNER_USERNAME))
async def send_msg(client, message):
    try:
        photo = 'photo.jpg'
        await message.delete()
        async def get_user_input(prompt):
            rply = await message.reply_text(prompt)
            link_msg = await app.listen(message.chat.id)
            await rply.delete()
            return link_msg.text
            
        start_msg_id = int(await extract_tg_link(await get_user_input("Send first post link")))
        end_msg_id = int(await extract_tg_link(await get_user_input("Send end post link")))

        batch_size = 199
        for start in range(start_msg_id, end_msg_id + 1, batch_size):
            end = min(start + batch_size - 1, end_msg_id)  # Ensure we don't go beyond end_msg_id
            file_messages = await app.get_messages(DB_CHANNEL_ID, range(start, end + 1))
            
            for file_message in file_messages:
                media = file_message.document or file_message.video
                if media:
                    caption = file_message.caption if file_message.caption else None
                    file_size = media.file_size if media.file_size else None

                    if caption:
                        new_caption = await remove_unwanted(caption)
                        cap_no_ext = await remove_extension(new_caption)
                        movie_name, release_year = await extract_movie_info(cap_no_ext)
                        poster_url = await get_movie_poster(movie_name, release_year)

                        try:
                            file_info = f"🗂️ <b>{escape(cap_no_ext)}</b>\n\n💾 <b>{humanbytes(file_size)}</b>"
                            file_link  = f"https://thetgflix.sshemw.workers.dev/bot1/{file_message.id}"

                            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Get File", url=file_link)]])

                            if poster_url:
                                # Send the message with the TMDb poster
                                await app.send_photo(CAPTION_CHANNEL_ID, poster_url, caption=file_info, reply_markup=keyboard)

                            else:
                                # If no movie details, fallback to default poster and caption
                                await app.send_photo(CAPTION_CHANNEL_ID, photo, caption=file_info, reply_markup=keyboard)

                            await asyncio.sleep(3)

                        except Exception as e:
                            logger.error(f'{e}')
                            # Fallback in case of any error
                            await app.send_photo(CAPTION_CHANNEL_ID, photo, caption=file_info, reply_markup=keyboard)
                            await asyncio.sleep(3)

        await message.reply_text("Messages send successfully ✅")

    except Exception as e:
        logger.error(f"Error in send commmand {e}")


@app.on_message(filters.command("copy") & filters.user(OWNER_USERNAME))
async def copy_msg(client, message):    
    try:
        await message.delete()
        async def get_user_input(prompt):
            rply = await message.reply_text(prompt)
            link_msg = await app.listen(message.chat.id)
            await rply.delete()
            return link_msg.text
        
        # Collect input from the user
        start_msg_id = int(await extract_tg_link(await get_user_input("Send first post link")))
        end_msg_id = int(await extract_tg_link(await get_user_input("Send end post link")))
        db_channel_id = int(await extract_channel_id(await get_user_input("Send db_channel link")))
        destination_id = int(await extract_channel_id(await get_user_input("Send destination channel link")))

        batch_size = 199
        for start in range(start_msg_id, end_msg_id + 1, batch_size):
            end = min(start + batch_size - 1, end_msg_id)  # Ensure we don't go beyond end_msg_id
            # Get and copy messages
            file_messages = await app.get_messages(db_channel_id, range(start, end + 1))

            for file_message in file_messages:
                if file_message and (file_message.document or file_message.video or file_message.audio or file_message.photo):
                    await file_message.copy(destination_id)
                    await asyncio.sleep(3)
                    
        await message.reply_text("Messages copied successfully!✅")
        
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f'{e}')

@app.on_message(filters.private & filters.command("info") & filters.user(OWNER_USERNAME))
async def getinfo_message(client, message):

    await message.delete()
    media_msg = await app.listen(message.chat.id, filters=(filters.video | filters.document))

    caption = media_msg.caption if media_msg.caption else None
    if caption:
        new_caption = await remove_unwanted(caption)
    try:
        movie_name, release_year = await extract_movie_info(new_caption)
        result = await get_by_name(movie_name, release_year)
        poster_url = result['poster_url']
        info = result['message']
        if poster_url:
            await app.send_photo(UPDATE_CHANNEL_ID, photo=poster_url, caption=info, parse_mode=enums.ParseMode.HTML)
            await media_msg.delete()
            await asyncio.sleep(3)

    except Exception as e:
        logger.error(f" info error {e}")

@app.on_message(filters.private & filters.command("tmdb") & filters.user(OWNER_USERNAME))
async def get_info(client, message):
    try:
        rply = await message.reply_text("Send TMDb link")

        # Listen for the next message (the TMDb URL)
        tmdb_msg = await app.listen(message.chat.id)

        # Extract the URL from the listened message
        tmdb_url = tmdb_msg.text

        result = await get_by_url(tmdb_url)
        poster_url = result['poster_url']
        caption = result['message']
        await app.send_photo(UPDATE_CHANNEL_ID, photo=poster_url, caption=caption, parse_mode=enums.ParseMode.HTML)
        await asyncio.sleep(3)
        await auto_delete_message(message, rply)
        await tmdb_msg.delete()
        await asyncio.sleep(3)
    except Exception as e:
        logger.error(f"{e}")


# Get Log Command
@app.on_message(filters.command("log") & filters.user(OWNER_USERNAME))
async def log_command(client, message):
    user_id = message.from_user.id

    # Send the log file
    try:
        reply = await app.send_document(user_id, document=LOG_FILE_NAME, caption="Bot Log File")
        await auto_delete_message(message, reply)
    except Exception as e:
        await app.send_message(user_id, f"Failed to send log file. Error: {str(e)}")

# Get Total User Command
@app.on_message(filters.command("users") & filters.user(OWNER_USERNAME))
async def total_users_command(client, message):
    user_id = message.from_user.id

    total_users = mongo_collection.count_documents({})
    response_text = f"Total number of users in the database: {total_users}"
    reply = await app.send_message(user_id, response_text)
    await auto_delete_message(message, reply)
            
async def verify_token(user_id, input_token):
    current_time = tm()

    # Check if the user_id exists in user_data
    if user_id not in user_data:
        return 'Token Mismatched ❌' 
    
    stored_token = user_data[user_id]['token']
    if input_token == stored_token:
        token = str(uuid.uuid4())
        user_data[user_id] = {"token": token, "time": current_time, "status": "verified", "file_count": 0}
        return f'Token Verified ✅ (Validity: {get_readable_time(TOKEN_TIMEOUT)})'
    else:
        return f'Token Mismatched ❌'
    
async def check_access(message, user_id):

    if user_id in user_data:
        time = user_data[user_id]['time']
        status = user_data[user_id]['status']
        file_count = user_data[user_id].get('file_count', 0)
        expiry = time + TOKEN_TIMEOUT
        current_time = tm()
        if current_time < expiry and status == "verified":
            if file_count < 10:
                return True
            else:
                reply = await message.reply_text(f"You have reached the limit. Please wait until the token expires")
                await auto_delete_message(message, reply)
                return False
        else:
            button = await update_token(user_id)
            send_message = await app.send_message(user_id, f"<b>It looks like your token has expired. Get Free 💎 Limited Access again!</b>", reply_markup=button)
            await auto_delete_message(message, send_message)
            return False
    else:
        button = await genrate_token(user_id)
        send_message = await app.send_message(user_id, f"<b>It looks like you don't have a token. Get Free 💎 Limited Access now!</b>", reply_markup=button)
        await auto_delete_message(message, send_message)
        return False

async def update_token(user_id):
    try:
        time = user_data[user_id]['time']
        expiry = time + TOKEN_TIMEOUT
        if time < expiry:
            token = user_data[user_id]['token']
        else:
            token = str(uuid.uuid4())
        current_time = tm()
        user_data[user_id] = {"token": token, "time": current_time, "status": "unverified", "file_count": 0}
        urlshortx = await shorten_url(f'https://telegram.me/{bot_username}?start=token_{token}')
        token_url = f'https://telegram.me/{bot_username}?start=token'
        button1 = InlineKeyboardButton("🎟️ Get Token", url=urlshortx)
        button2 = InlineKeyboardButton("👨‍🏫 How it Works", url=token_url)
        button = InlineKeyboardMarkup([[button1], [button2]]) 
        return button
    except Exception as e:
        logger.error(f"error in update_token: {e}")

async def genrate_token(user_id):
    try:
        token = str(uuid.uuid4())
        current_time = tm()
        user_data[user_id] = {"token": token, "time": current_time, "status": "unverified", "file_count": 0}
        urlshortx = await shorten_url(f'https://telegram.me/{bot_username}?start=token_{token}')
        token_url = f'https://telegram.me/{bot_username}?start=token'
        button1 = InlineKeyboardButton("🎟️ Get Token", url=urlshortx)
        button2 = InlineKeyboardButton("👨‍🏫 How it Works", url=token_url)
        button = InlineKeyboardMarkup([[button1], [button2]]) 
        return button
    except Exception as e:
        logger.error(f"error in genrate_token: {e}")

async def get_user_link(user: User) -> str:
    user_id = user.id
    first_name = user.first_name
    return f'<a href=tg://user?id={user_id}>{first_name}</a>'
      
if __name__ == "__main__":
    logger.info("Bot is starting...")
    loop.run_until_complete(main())
    logger.info("Bot has stopped.")
