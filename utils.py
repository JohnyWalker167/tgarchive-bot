import re
import requests
import string
import aiohttp
import asyncio
from config import *
from pyrogram.types import User

translator = str.maketrans('', '', string.punctuation.replace('#', ''))

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
    
async def get_quality(caption):
    try:
        # Use regular expressions to check for resolution patterns in the caption
        if re.search(r'720p', caption, re.IGNORECASE):
            return '720p'
        elif re.search(r'1080p', caption, re.IGNORECASE):
            return '1080p'
        elif re.search(r'2160p', caption, re.IGNORECASE):
            return '2160p'
        else:
            return None  # Default if no resolution is found
    except Exception as e:
        logger.error(e)
        return None
    
async def extract_season_episode(filename):
    # Regex to find the season and episode pattern
    match = re.search(r'S(\d{2})(?:E(\d{2}))?', filename, re.IGNORECASE)
    if match:
        season_no = f"S{match.group(1)}"
        episode_no = f"E{match.group(2)}" if match.group(2) else None
        
        return season_no, episode_no
    return None, None

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
            # Replace '.' and remove '(' and ')' from movie_name
            movie_name = match.group(1).replace('.', ' ').replace('(', '').replace(')', '').strip()
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

                if search_data.get('results', []):
                    # Filter results based on release year and first air date
                    matching_results = [
                        result for result in search_data['results']
                        if ('release_date' in result and result['release_date'][:4] == str(release_year)) or
                        ('first_air_date' in result and result['first_air_date'][:4] == str(release_year))
                    ]

                    if matching_results:
                        result = matching_results[0]

                        # Fetch additional details using movie ID
                        movie_id = result['id']
                        media_type = result['media_type']

                        # Details URL for additional movie/TV show information
                        tmdb_movie_details_url = f'https://api.themoviedb.org/3/{media_type}/{movie_id}?api_key={TMDB_API_KEY}&language=en-US'

                        async with session.get(tmdb_movie_details_url) as details_response:
                            details_data = await details_response.json()

                        # Fetch additional image details (poster/backdrop)
                        tmdb_movie_image_url = f'https://api.themoviedb.org/3/{media_type}/{movie_id}/images?api_key={TMDB_API_KEY}&language=en-US&include_image_language=en,hi'

                        async with session.get(tmdb_movie_image_url) as movie_response:
                            movie_images = await movie_response.json()

                        # Get the poster or backdrop path (check if list is not empty)
                        poster_path = None
                        if movie_images.get('backdrops'):
                            poster_path = movie_images['backdrops'][0].get('file_path')
                        elif result.get('backdrop_path'):
                            poster_path = result['backdrop_path']
                        elif result.get('poster_path'):
                            poster_path = result['poster_path']

                        # Ensure poster path is not None
                        poster_url = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else None

                        # Extract additional details with robust checks
                        title = details_data.get('title') or details_data.get('name')
                        spoken_languages = [lang['english_name'] for lang in details_data.get('spoken_languages', [])] if details_data.get('spoken_languages') else None
                        genres = ' '.join([f"#{genre['name'].replace(' ', '')}" for genre in details_data.get('genres', [])]).strip() if details_data.get('genres') else None
                        if genres:
                            genres = genres.translate(translator)
                        collection_name = f"#{details_data.get('belongs_to_collection', {}).get('name', '').replace(' ', '')}".strip() if details_data.get('belongs_to_collection') else None
                        if collection_name:
                            collection_name = collection_name.translate(translator) 
                        runtime = details_data.get('runtime') or (details_data.get('episode_run_time', [None])[0] if details_data.get('episode_run_time') else None)
                        release_date = details_data.get('release_date') or details_data.get('first_air_date')
                        tagline = details_data.get('tagline')
                        vote_average = int(details_data.get('vote_average'))


                        # Return all the details, ensuring empty fields are handled
                        return {
                            'poster_url': poster_url,
                            'title': title,
                            'spoken_languages': spoken_languages if spoken_languages else None,
                            'genres': genres if genres else None,
                            'collection_name': collection_name,
                            'runtime': runtime,
                            'release_date': release_date,
                            'tagline': tagline,
                            'vote_average': vote_average
                        }

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

async def get_movie_poster_by_id(media_type, movie_id):
    try:
        async with aiohttp.ClientSession() as session:
            # Details URL for additional movie/TV show information
            tmdb_movie_details_url = f'https://api.themoviedb.org/3/{media_type}/{movie_id}?api_key={TMDB_API_KEY}&language=en-US'

            async with session.get(tmdb_movie_details_url) as details_response:
                details_data = await details_response.json()

                # Fetch additional image details (poster/backdrop)
                tmdb_movie_image_url = f'https://api.themoviedb.org/3/{media_type}/{movie_id}/images?api_key={TMDB_API_KEY}&language=en-US&include_image_language=en,hi'

                async with session.get(tmdb_movie_image_url) as movie_response:
                    movie_images = await movie_response.json()

                    # Get the poster or backdrop path (check if list is not empty)
                    poster_path = None
                    if movie_images.get('backdrops'):
                        poster_path = movie_images['backdrops'][0].get('file_path')
                    elif details_data.get('backdrop_path'):
                        poster_path = details_data['backdrop_path']
                    elif details_data.get('poster_path'):
                        poster_path = details_data['poster_path']

                    # Ensure poster path is not None
                    poster_url = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else None

                    # Extract additional details with robust checks
                    title = details_data.get('title') or details_data.get('name')
                    spoken_languages = [lang['english_name'] for lang in details_data.get('spoken_languages', [])] if details_data.get('spoken_languages') else None
                    genres = ' '.join([f"#{genre['name'].replace(' ', '')}" for genre in details_data.get('genres', [])]).strip() if details_data.get('genres') else None
                    if genres:
                        genres = genres.translate(translator)                    
                    collection_name = f"#{details_data.get('belongs_to_collection', {}).get('name', '').replace(' ', '')}".strip() if details_data.get('belongs_to_collection') else None
                    if collection_name:
                        collection_name = collection_name.translate(translator) 
                    runtime = details_data.get('runtime') or (details_data.get('episode_run_time', [None])[0] if details_data.get('episode_run_time') else None)
                    release_date = details_data.get('release_date') or details_data.get('first_air_date')
                    tagline = details_data.get('tagline')
                    vote_average = int(details_data.get('vote_average'))

                    # Return all the details, ensuring empty fields are handled
                    return {
                        'poster_url': poster_url,
                        'title': title,
                        'spoken_languages': spoken_languages if spoken_languages else None,
                        'genres': genres if genres else None,
                        'collection_name': collection_name,
                        'runtime': runtime,
                        'release_date': release_date,
                        'tagline': tagline,
                        'vote_average': vote_average  # Keep float for precision
                    }

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

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

async def extract_tmdb_link(tmdb_url):
    movie_pattern = r'themoviedb\.org\/movie\/(\d+)'
    tv_pattern = r'themoviedb\.org\/tv\/(\d+)'
    
    if re.search(movie_pattern, tmdb_url):
        tmdb_type = 'movie'
        tmdb_id = re.search(movie_pattern, tmdb_url).group(1)
    elif re.search(tv_pattern, tmdb_url):
        tmdb_type = 'tv'
        tmdb_id = re.search(tv_pattern, tmdb_url).group(1)
    return tmdb_type, tmdb_id
