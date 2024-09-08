import os
import uuid
from utils import *
from config import *
from time import time as tm
from pyrogram import idle
from pyromod import listen
from pyrogram.errors import FloodWait
from pyrogram import Client, filters, enums, types
from shorterner import *
from asyncio import get_event_loop
from pymongo import MongoClient
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from tmdb import get_tmdb_info

loop = get_event_loop()

MONGO_COLLECTION = "users"
mongo_client = MongoClient(MONGO_URL)
mongo_db = mongo_client[MONGO_DB_NAME]
mongo_collection = mongo_db[MONGO_COLLECTION]

user_data = {}
TOKEN_TIMEOUT = 7200

spoiler_settings = {}

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

@app.on_message(filters.private & (filters.document | filters.video | filters.photo) & filters.user(OWNER_USERNAME))
async def pyro_task(client, message):
    caption = message.caption if message.caption else None
    if caption:
        new_caption = await remove_unwanted(caption)
        no_ext = await remove_extension(new_caption)
    # Initialize the has_spoiler setting for this task/message
    spoiler_settings[message.id] = False

    rply = await message.reply_text(
        f"Please send a photo\nSelect the spoiler setting:",
        reply_markup=types.InlineKeyboardMarkup(
            [
                [types.InlineKeyboardButton("True", callback_data=f"set_spoiler_true_{message.id}")],
                [types.InlineKeyboardButton("False", callback_data=f"set_spoiler_false_{message.id}")]
            ]
        )
    )
    
    photo_msg = await app.listen(message.chat.id, filters=filters.photo)
    
    thumb_path = await app.download_media(photo_msg, file_name=f'photo_{message.id}.jpg')
    await photo_msg.delete()
    await rply.delete()
    
    try:
        cpy_msg = await message.copy(DB_CHANNEL_ID, caption=f"<code>{new_caption}</code>", parse_mode=enums.ParseMode.HTML)
        await message.delete()
        file_info = f"🎞️ <b>{no_ext}</b>\n\n🆔 <code>{cpy_msg.id}</code>"
        await app.send_photo(CAPTION_CHANNEL_ID, thumb_path, caption=file_info, has_spoiler=spoiler_settings[message.id])
        await asyncio.sleep(3)
        
    except Exception as e:
        logger.error(f'{e}')
    finally:
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
        # Clean up the spoiler setting for this message ID
        spoiler_settings.pop(message.id, None)

@app.on_callback_query(filters.regex(r"set_spoiler_(true|false)_\d+"))
async def spoiler_callback(client, callback_query):
    data_parts = callback_query.data.split('_')
    spoiler_value = data_parts[2] == "true"
    message_id = int(data_parts[3])
    
    # Update the dictionary with the new has_spoiler value for this task
    spoiler_settings[message_id] = spoiler_value
    await callback_query.answer(f"Set to {spoiler_value}")
        
'''          
@app.on_message(filters.private & filters.command("tmdb") & filters.user(OWNER_USERNAME))
async def get_info(client, message):
    rply = await message.reply_text("Send TMDb link")

    # Listen for the next message (the TMDb URL)
    tmdb_msg = await app.listen(message.chat.id)

    # Extract the URL from the listened message
    tmdb_url = tmdb_msg.text

    result = await get_tmdb_info(tmdb_url)
    poster_url = result['poster_url']
    caption = result['message']
    await app.send_photo(CAPTION_CHANNEL_ID, photo=poster_url, caption=caption, parse_mode=enums.ParseMode.HTML)
    await auto_delete_message(message, rply)
    await tmdb_msg.delete()
    await asyncio.sleep(3)
'''


@app.on_message(filters.private & filters.command("start"))
async def get_command(client, message): 
     input_token = message.command[1] if len(message.command) > 1 else None
     user_id = message.from_user.id
     user_link = await get_user_link(message.from_user)

     if input_token:
          token_msg = await verify_token(user_id, input_token)
          reply = await message.reply_text(token_msg)
          await app.send_message(LOG_CHANNEL_ID, f"User🕵️‍♂️{user_link} with 🆔 {user_id} @{bot_username} {token_msg}", parse_mode=enums.ParseMode.HTML)
          await auto_delete_message(message, reply)
     else:
        mongo_collection.update_one(
                {'user_id': user_id},
                {'$set': {'user_id': user_id}}, 
                upsert=True
            )
        reply = await message.reply_text(f"<b>💐Welcome this is TG⚡️Flix Bot")
        await auto_delete_message(message, reply)


# Get Command      
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
                    new_caption = await remove_extension(caption.html)
                    copy_message = await file_message.copy(chat_id=message.chat.id, caption=f"<code>{new_caption}</code>", parse_mode=enums.ParseMode.HTML)
                else:
                    copy_message = await file_message.copy(chat_id=message.chat.id)

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
                copy_message = await file_message.copy(chat_id=message.chat.id, caption=f"<code>{new_caption}</code>", parse_mode=enums.ParseMode.HTML)
            else:
                copy_message = await file_message.copy(chat_id=message.chat.id)

            await auto_delete_message(message, copy_message)
            await asyncio.sleep(3)
    else:
        reply = await message.reply_text("Provide a File Id")
        await auto_delete_message(message, reply)  
       
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
    
# Help Command
@app.on_message(filters.private & filters.command("help"))
async def handle_help_command(client, message):
    try:
        file_id = 3
        get_msg = await app.get_messages(DB_CHANNEL_ID, int(file_id))
        send_msg = await get_msg.copy(chat_id=message.chat.id)
        await message.delete()
        await asyncio.sleep(300)
        await send_msg.delete()
    except Exception as e:
        logger.error(f"{e}")
        
async def verify_token(user_id, input_token):
    current_time = tm()

    # Check if the user_id exists in user_data
    if user_id not in user_data:
        return 'Token Mismatched ❌' 
    
    stored_token = user_data[user_id]['token']
    if input_token == stored_token:
        token = str(uuid.uuid4())
        user_data[user_id] = {"token": token, "time": current_time, "status": "verified"}
        return f'Token Verified ✅'
    else:
        return f'Token Mismatched ❌'
    
async def check_access(message, user_id):

    if user_id in user_data:
        time = user_data[user_id]['time']
        status = user_data[user_id]['status']
        expiry = time + TOKEN_TIMEOUT
        current_time = tm()
        if current_time < expiry and status == "verified":
            return True
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
        user_data[user_id] = {"token": token, "time": current_time, "status": "unverified"}
        urlshortx = await shorten_url(f'https://telegram.me/{bot_username}?start={token}')
        button = InlineKeyboardMarkup([[InlineKeyboardButton("Collect Token", url=urlshortx)]])
        return button
    except Exception as e:
        logger.error(f"error in update_token: {e}")

async def genrate_token(user_id):
    try:
        token = str(uuid.uuid4())
        current_time = tm()
        user_data[user_id] = {"token": token, "time": current_time, "status": "unverified"}
        urlshortx = await shorten_url(f'https://telegram.me/{bot_username}?start={token}')
        button = InlineKeyboardMarkup([[InlineKeyboardButton("Collect Token", url=urlshortx)]])
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
