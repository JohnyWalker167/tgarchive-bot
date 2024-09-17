import uuid
from utils import *
from config import *
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

user = Client(
                "userbot",
                api_id=int(API_ID),
                api_hash=API_HASH,
                session_string=STRING_SESSION,
                no_updates = True
            )

async def main():
    async with app, user:
        await idle()

with app:
    bot_username = (app.get_me()).username

@app.on_message(filters.private & filters.command("start"))
async def get_command(client, message): 
     user_id = message.from_user.id
     user_link = await get_user_link(message.from_user)

     if len(message.command) > 1 and message.command[1] == "token":
        try:
            file_id = 4
            get_msg = await app.get_messages(DB_CHANNEL_ID, int(file_id))
            cpy_msg = await get_msg.copy(chat_id=message.chat.id)
            await auto_delete_message(message, cpy_msg)
            
        except Exception as e:
            logger.error(f"{e}")
        return

     if len(message.command) > 1 and len(message.command[1]) == 36:
         input_token = message.command[1] if len(message.command) > 1 else None
         token_msg = await verify_token(user_id, input_token)
         reply = await message.reply_text(token_msg)
         await app.send_message(LOG_CHANNEL_ID, f"User🕵️‍♂️{user_link} with 🆔 {user_id} @{bot_username} {token_msg}", parse_mode=enums.ParseMode.HTML)
         await auto_delete_message(message, reply)
         return
     
     else:
        mongo_collection.update_one(
                {'user_id': user_id},
                {'$set': {'user_id': user_id}}, 
                upsert=True
            )
        reply = await message.reply_text(f"<b>💐Welcome this is TG⚡️Flix Bot")
        await auto_delete_message(message, reply)

@app.on_message(filters.private & filters.command("get"))
async def handle_get_command(client, message):
    user_id = message.from_user.id
    if not await check_access(message, user_id):
         return
    
    file_id = message.command[1] if len(message.command) > 1 else None

    if file_id:
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
            user_data[user_id]['file_count'] += 1
            await asyncio.sleep(3)
    else:
        reply = await message.reply_text("Provide a File Id")
        await auto_delete_message(message, reply)  

@app.on_message(filters.private & (filters.document | filters.video) & filters.user(OWNER_USERNAME))
async def forward_message_to_new_channel(client, message):
    media = message.document or message.video
    
    if media:
        caption = message.caption if message.caption else None
        file_size = media.file_size if media.file_size else None

        if caption:
            new_caption = await remove_unwanted(caption)
            cap_no_ext = await remove_extension(new_caption)
            movie_name, release_year = await extract_movie_info(cap_no_ext)
            poster_url = await get_movie_poster(movie_name, release_year)


            try:
                cpy_msg = await message.copy(DB_CHANNEL_ID, caption=f"<code>{escape(new_caption)}</code>", parse_mode=enums.ParseMode.HTML)
                await message.delete()

                if poster_url:
                    file_info = f"<b>🗂️ {escape(cap_no_ext)}\n\n💾 {humanbytes(file_size)}   🆔 <code>{cpy_msg.id}</code></b>"
                    # Send the message with the TMDb poster
                    await app.send_photo(CAPTION_CHANNEL_ID, poster_url, caption=file_info)
                else:
                    # If no movie details, fallback to default poster and caption
                    await app.send_message(LOG_CHANNEL_ID, text=f"<code>{new_caption}</code>")

            except Exception as e:
                logger.error(f'{e}')
                # Fallback in case of any error
                await app.send_message(LOG_CHANNEL_ID, text=f"<code>{new_caption}</code>")
                await asyncio.sleep(3)

    if message.photo:
        await message.copy(CAPTION_CHANNEL_ID)
        await message.delete()
        

@app.on_message(filters.private & filters.command("send") & filters.user(OWNER_USERNAME))
async def send_msg(client, message):
    try:
        await message.delete()
        async def get_user_input(prompt):
            rply = await message.reply_text(prompt)
            link_msg = await app.listen(message.chat.id)
            await link_msg.delete()
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
                            if poster_url:
                                file_info = f"<b>🗂️ {escape(cap_no_ext)}\n\n💾 {humanbytes(file_size)}   🆔 <code>{file_message.id}</code></b>"
                                # Send the message with the TMDb poster
                                await app.send_photo(CAPTION_CHANNEL_ID, poster_url, caption=file_info)

                            else:
                                # If no movie details, fallback to default poster and caption
                                await app.send_message(LOG_CHANNEL_ID, text=f"<code>{new_caption}</code>")

                            await asyncio.sleep(3)

                        except Exception as e:
                            logger.error(f'{e}')
                            # Fallback in case of any error
                            await app.send_message(LOG_CHANNEL_ID, text=f"<code>{new_caption}</code>")
                            await asyncio.sleep(3)

        await message.reply_text("Messages send successfully ✅")

    except Exception as e:
        logger.error(f"Error in send commmand {e}")

@app.on_message(filters.private & filters.command("tmdb") & filters.user(OWNER_USERNAME))
async def forward_message_to_new_channel(client, message):
    try:
        await message.delete()
        async def get_user_input(prompt):
            rply = await message.reply_text(prompt)
            link_msg = await app.listen(message.chat.id)
            await link_msg.delete()
            await rply.delete()
            return link_msg.text

        msg_id = int(await extract_tg_link(await get_user_input("Send post link")))
        type, id = await extract_tmdb_link(await get_user_input("Send tmdb link"))

        file_message = await app.get_messages(DB_CHANNEL_ID, msg_id)
        media = file_message.document or file_message.video

        if media:
            caption = file_message.caption if file_message.caption else None
            file_size = media.file_size if media.file_size else None

            if caption:
                new_caption = await remove_unwanted(caption)
                cap_no_ext = await remove_extension(new_caption)
                poster_url = await get_movie_poster_by_id(type, id)

                try:
                    if poster_url:
                        file_info = f"<b>🗂️ {escape(cap_no_ext)}\n\n💾 {humanbytes(file_size)}   🆔 <code>{file_message.id}</code></b>"
                        # Send the message with the TMDb poster
                        await app.send_photo(CAPTION_CHANNEL_ID, poster_url, caption=file_info)
                    else:
                        async def get_user_input(prompt):
                            rply = await message.reply_text(prompt)
                            photo_msg = await app.listen(message.chat.id, filters=filters.photo)
                            await photo_msg.delete()
                            await rply.delete()
                            return photo_msg
                        
                        poster = await get_user_input("Send first post link")

                        # If no movie details, fallback to default poster and caption
                        await app.send_photo(CAPTION_CHANNEL_ID, poster, caption=file_info)

                except Exception as e:
                    logger.error(f'{e}')
                    # Fallback in case of any error
                    async def get_user_input(prompt):
                        rply = await message.reply_text(prompt)
                        photo_msg = await app.listen(message.chat.id, filters=filters.photo)
                        await photo_msg.delete()
                        await rply.delete()
                        return photo_msg
                    
                    poster = await get_user_input("Send first post link")

                    # If no movie details, fallback to default poster and caption
                    await app.send_photo(CAPTION_CHANNEL_ID, poster, caption=file_info)

    except Exception as e:
        logger.error(f"{e}")

@app.on_message(filters.command("copy") & filters.user(OWNER_USERNAME))
async def copy_msg(client, message):    
    try:
        await message.delete()
        async def get_user_input(prompt):
            rply = await message.reply_text(prompt)
            link_msg = await app.listen(message.chat.id)
            await link_msg.delete()
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
                    caption = file_message.caption.html if file_message.caption else None
                    await file_message.copy(destination_id, caption=caption)
                    await asyncio.sleep(3)
                    
        await message.reply_text("Messages copied successfully!✅")
        
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f'{e}')

# Delete Commmand
@app.on_message(filters.command("delete") & filters.user(OWNER_USERNAME))
async def delete_command(client, message):
    try:
        await message.reply_text("Enter channel_id")
        channel_id = int((await app.listen(message.chat.id)).text)

        await message.reply_text("Enter count")
        limit = int((await app.listen(message.chat.id)).text)

        await app.send_message(channel_id, "Hi")

        try:
            async for message in user.get_chat_history(channel_id, limit):
                await message.delete()
        except Exception as e:
            logger.error(f"Error deleting messages: {e}")
        await user.send_message(channel_id, "done")
    except Exception as e:
        logger.error(f"Error : {e}")

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
        return f'Token Verified ✅'
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
        else:
            button = await update_token(user_id)
            send_message = await app.send_message(user_id,f'<b>You need to collect your token first 🎟\n(Valid: {get_readable_time(TOKEN_TIMEOUT)})</b>', reply_markup=button)
            await auto_delete_message(message, send_message)
    else:
        button = await genrate_token(user_id)
        send_message = await app.send_message(user_id,f'<b>You need to collect your token first 🎟\n(Valid: {get_readable_time(TOKEN_TIMEOUT)})</b>', reply_markup=button)
        await auto_delete_message(message, send_message)

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
        urlshortx = await shorten_url(f'https://telegram.me/{bot_username}?start={token}')
        token_url = f'https://telegram.me/{bot_username}?start=token'
        button1 = InlineKeyboardButton("Collect Token", url=urlshortx)
        button2 = InlineKeyboardButton("How to Bypass Token", url=token_url)
        button = InlineKeyboardMarkup([[button1, button2]])
        return button
    except Exception as e:
        logger.error(f"error in update_token: {e}")

async def genrate_token(user_id):
    try:
        token = str(uuid.uuid4())
        current_time = tm()
        user_data[user_id] = {"token": token, "time": current_time, "status": "unverified", "file_count": 0}
        urlshortx = await shorten_url(f'https://telegram.me/{bot_username}?start={token}')
        token_url = f'https://telegram.me/{bot_username}?start=token'
        button1 = InlineKeyboardButton("Collect Token", url=urlshortx)
        button2 = InlineKeyboardButton("How to Bypass Token", url=token_url)
        button = InlineKeyboardMarkup([[button1, button2]])
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
