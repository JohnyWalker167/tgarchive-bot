import re
import requests
import aiohttp
import asyncio
from config import *
from pyrogram.types import User

POSTER_BASE_URL = 'https://image.tmdb.org/t/p/original'

MAX_OVERVIEW_LENGTH = 500  # Limit overview to 500 characters to prevent exceeding Telegram's limit.

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
    
async def get_sticker(caption):
    small = "CAACAgUAAxkBAAEbIPRm3zyR_cJSsuHrFaWtFTL0Fxg4VQACLQgAAo2CIFdu8Xb02-Ck1zYE"
    big = "CAACAgUAAxkBAAEbIMhm3zIgOvPwF7Vpgok2-1pe1PrXywAC1gkAAqzNKVfogSiZyNQ8WDYE"
    large = "CAACAgUAAxkBAAEbIPhm3z0DFCfiB0J_BmpjzslA3YuOwAAC8wYAAtXJOVVPrZPulHguKjYE"

    try:
        # Use regular expressions to check for resolution patterns in the caption
        if re.search(r'720p', caption, re.IGNORECASE):
            return small
        elif re.search(r'1080p', caption, re.IGNORECASE):
            return big
        elif re.search(r'2160p', caption, re.IGNORECASE):
            return large
        else:
            return None   # Default sticker if no resolution is found
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

async def get_user_link(user: User) -> str:
    user_id = user.id
    first_name = user.first_name
    return f'<a href=tg://user?id={user_id}>{first_name}</a>'

async def extract_movie_info(caption):
    try:
        regex = re.compile(r'(.+?)(\d{4})')
        match = regex.search(caption)

        if match:
             movie_name = match.group(1).replace('.', ' ').strip()
             release_year = match.group(2)
             return movie_name, release_year
    except Exception as e:
        print(e)
    return None, None

async def get_movie_poster(movie_name, release_year):
    tmdb_search_url = f'https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={movie_name}'
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(tmdb_search_url) as search_response:
                search_data = await search_response.json()

                if search_data['results']:
                    # Filter results based on release year and first air date
                    matching_results = [
                        result for result in search_data['results']
                        if ('release_date' in result and result['release_date'][:4] == str(release_year)) or
                        ('first_air_date' in result and result['first_air_date'][:4] == str(
                            release_year))
                    ]

                    if matching_results:
                        result = matching_results[0]

                        # Fetch additional details using movie ID
                        movie_id = result['id']
                        media_type = result['media_type']

                        api_url = f"https://api.themoviedb.org/3/{media_type}/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
                        
                        response = requests.get(api_url)
                        response.raise_for_status()
                        data = response.json()
                        message = format_tmdb_info(media_type, data)
                        poster_url = POSTER_BASE_URL + data.get('poster_path') if data.get('poster_path') else None
                        return {"message": message, "poster_url": poster_url}
                                                   
    except requests.exceptions.RequestException as e:
        print(f"Error fetching TMDB data: {e}")
    return {"message": f"Error: {str(e)}", "poster_url": None}


def format_tmdb_info(tmdb_type, data):
    """
    Formats TMDb API response into a user-friendly HTML message.

    Args:
    - tmdb_type (str): The type of TMDb entity ('movie', 'tv', 'collection').
    - data (dict): The API response containing details of the entity.

    Returns:
    - str: Formatted string to be sent as a Telegram message using HTML.
    """
    if tmdb_type == 'movie':
        genres = ", ".join([genre['name'] for genre in data.get('genres', [])])
        runtime = f"{data.get('runtime', 'N/A')} minutes"
        overview = truncate_overview(data.get('overview', 'N/A'))
        
        message = (
            f"🎬 <b>{data.get('title', 'N/A')}</b>\n"
            f"🗓 <b>Release Date:</b> {data.get('release_date', 'N/A')}\n"
            f"⭐ <b>Rating:</b> {data.get('vote_average', 'N/A')} ({data.get('vote_count', '0')} votes)\n"
            f"🎥 <b>Runtime:</b> {runtime}\n"
            f"🎭 <b>Genres:</b> {genres}\n"
            f"📃 <b>Overview:</b> {overview}\n"
        )
        
    elif tmdb_type == 'tv':
        genres = ", ".join([genre['name'] for genre in data.get('genres', [])])
        num_episodes = data.get('number_of_episodes', 'N/A')
        num_seasons = data.get('number_of_seasons', 'N/A')
        overview = truncate_overview(data.get('overview', 'N/A'))
        
        message = (
            f"📺 <b>{data.get('name', 'N/A')}</b>\n"
            f"🗓 <b>First Air Date:</b> {data.get('first_air_date', 'N/A')}\n"
            f"⭐ <b>Rating:</b> {data.get('vote_average', 'N/A')} ({data.get('vote_count', '0')} votes)\n"
            f"📅 <b>Number of Seasons:</b> {num_seasons}\n"
            f"📺 <b>Number of Episodes:</b> {num_episodes}\n"
            f"🎭 <b>Genres:</b> {genres}\n"
            f"📃 <b>Overview:</b> {overview}\n"
        )
        
    elif tmdb_type == 'collection':
        parts = data.get('parts', [])
        overview = truncate_overview(data.get('overview', 'N/A'))
        
        message = (
            f"🎞 <b>{data.get('name', 'N/A')}</b>\n"
            f"🎬 <b>Number of Movies:</b> {len(parts)}\n"
            f"📃 <b>Overview:</b> {overview}\n"
        )
    else:
        message = "Unknown type. Unable to format information."
    
    return message

def truncate_overview(overview):
    """
    Truncate the overview if it exceeds the specified limit.

    Args:
    - overview (str): The overview text from the API.

    Returns:
    - str: Truncated overview with an ellipsis if it exceeds the limit.
    """
    if len(overview) > MAX_OVERVIEW_LENGTH:
        return overview[:MAX_OVERVIEW_LENGTH] + "..."
    return overview
