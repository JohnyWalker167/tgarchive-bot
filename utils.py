import re
import aiohttp
import asyncio
from config import *

async def auto_delete_message(user_message, bot_message):
    try:
        await user_message.delete()
        await asyncio.sleep(60)
        await bot_message.delete()
    except Exception as e:
        logger.error(f"{e}")
        
def get_readable_time(seconds: int) -> str:
    result = ""
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f"{days}d"
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f"{hours}h"
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f" {minutes}m"
    seconds = int(seconds)
    result += f" {seconds}s"
    return result
    
async def remove_extension(caption):
    try:
        # Remove .mkv and .mp4 extensions if present
        cleaned_caption = re.sub(r'\.mkv|\.mp4|\.webm', '', caption)
        return cleaned_caption
    except Exception as e:
        logger.error(e)
        return None

async def remove_unwanted(input_string):
    # Use regex to match .mkv or .mp4 and everything that follows
    result = re.split(r'(\.mkv|\.mp4)', input_string)
    # Join the first two parts to get the string up to the extension
    return ''.join(result[:2])

def humanbytes(size):
    # Function to format file size in a human-readable format
    if not size:
        return "0 B"
    # Define byte sizes
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    while size >= 1024 and i < len(suffixes) - 1:
        size /= 1024
        i += 1
    f = ('%.2f' % size).rstrip('0').rstrip('.')
    return f"{f} {suffixes[i]}"


async def extract_tg_link(telegram_link):
    try:
        pattern = re.compile(r'https://t\.me/c/(-?\d+)/(\d+)')
        match = pattern.match(telegram_link)
        if match:
            message_id = match.group(2)
            return message_id
        else:
            return None
    except Exception as e:
        logger.error(e)
        
async def extract_channel_id(telegram_link):
    try:
        pattern = re.compile(r'https://t\.me/c/(-?\d+)/(\d+)')
        match = pattern.match(telegram_link)
        if match:
            channel_id = match.group(1)
            formatted_channel_id = f'-100{channel_id}'
            return formatted_channel_id
        else:
            return None
    except Exception as e:
        logger.error(e)
