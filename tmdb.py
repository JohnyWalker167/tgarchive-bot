import requests
import re
from config import TMDB_API_KEY

POSTER_BASE_URL = 'https://image.tmdb.org/t/p/original'

MAX_OVERVIEW_LENGTH = 500  # Limit overview to 500 characters to prevent exceeding Telegram's limit.

async def get_tmdb_info(tmdb_url):
    """
    Fetches and formats information from TMDb based on the given URL for movie, TV show, or collection.
    
    Args:
    - tmdb_url (str): TMDb URL provided by the user.

    Returns:
    - dict: Dictionary containing formatted message and poster URL.
    """
    
    # Regular expressions to capture TMDb ID and type (movie, tv, collection)
    movie_pattern = r'themoviedb\.org\/movie\/(\d+)'
    tv_pattern = r'themoviedb\.org\/tv\/(\d+)'
    collection_pattern = r'themoviedb\.org\/collection\/(\d+)'
    
    if re.search(movie_pattern, tmdb_url):
        tmdb_type = 'movie'
        tmdb_id = re.search(movie_pattern, tmdb_url).group(1)
    elif re.search(tv_pattern, tmdb_url):
        tmdb_type = 'tv'
        tmdb_id = re.search(tv_pattern, tmdb_url).group(1)
    elif re.search(collection_pattern, tmdb_url):
        tmdb_type = 'collection'
        tmdb_id = re.search(collection_pattern, tmdb_url).group(1)
    else:
        return {"message": "Invalid TMDb URL. Please provide a valid movie, TV show, or collection URL."}
    
    # Build the API request URL based on the type
    api_url = f"https://api.themoviedb.org/3/{tmdb_type}/{tmdb_id}?api_key={TMDB_API_KEY}&language=en-US"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        message = format_tmdb_info(tmdb_type, data)
        poster_url = POSTER_BASE_URL + data.get('poster_path') if data.get('poster_path') else None
        return {"message": message, "poster_url": poster_url}
    except requests.exceptions.RequestException as e:
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
            f"🎞 <b>Original Language:</b> {data.get('original_language', 'N/A')}"
        )
        
    elif tmdb_type == 'collection':
        parts = data.get('parts', [])
        movie_titles = ", ".join([movie['title'] for movie in parts]) or "N/A"
        overview = truncate_overview(data.get('overview', 'N/A'))
        
        message = (
            f"🎞 <b>{data.get('name', 'N/A')}</b>\n"
            f"🎬 <b>Number of Movies:</b> {len(parts)}\n"
            f"🎥 <b>Movies in Collection:</b> {movie_titles}\n"
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
