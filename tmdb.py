import re
import aiohttp
from config import TMDB_API_KEY

POSTER_BASE_URL = 'https://image.tmdb.org/t/p/original'

async def get_by_name(movie_name, release_year):
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
                        ('first_air_date' in result and result['first_air_date'][:4] == str(release_year))
                    ]

                    if matching_results:
                        result = matching_results[0]

                        # Fetch additional details using movie ID
                        movie_id = result['id']
                        media_type = result['media_type']

                        api_url = f"https://api.themoviedb.org/3/{media_type}/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"

                        tmdb_movie_image_url = f'https://api.themoviedb.org/3/{media_type}/{movie_id}/images?api_key={TMDB_API_KEY}&language=en-US&include_image_language=en,hi'

                        async with session.get(api_url) as detail_response:
                            data = await detail_response.json()
                        async with session.get(tmdb_movie_image_url) as movie_response:
                            movie_images = await movie_response.json()

                            message = await format_tmdb_info(media_type, movie_id, data)

                            poster_path = result.get('poster_path', None)
                            if 'backdrops' in movie_images and movie_images['backdrops']:
                                poster_path = movie_images['backdrops'][0]['file_path']
                            elif 'posters' in movie_images and movie_images['posters']:
                                poster_path = movie_images['posters'][0]['file_path']
                            if poster_path:
                                 poster_url = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else None
                            return {"message": message, "poster_url": poster_url}

    except aiohttp.ClientError as e:
        print(f"Error fetching TMDB data: {e}")
    return {"message": f"Error: {str(e)}", "poster_url": None}

async def get_by_url(tmdb_url):
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

    tmdb_movie_image_url = f'https://api.themoviedb.org/3/{tmdb_type}/{tmdb_id}/images?api_key={TMDB_API_KEY}&language=en-US&include_image_language=en,hi'

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as detail_response:
                data = await detail_response.json()
            async with session.get(tmdb_movie_image_url) as movie_response:
                movie_images = await movie_response.json()


                message = await format_tmdb_info(tmdb_type, tmdb_id, data)

                poster_path = data.get('poster_path', None)
                if 'backdrops' in movie_images and movie_images['backdrops']:
                    poster_path = movie_images['backdrops'][0]['file_path']
                elif 'posters' in movie_images and movie_images['posters']:
                    poster_path = movie_images['posters'][0]['file_path']
                if poster_path:
                     poster_url = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else None
                return {"message": message, "poster_url": poster_url}

    except aiohttp.ClientError as e:
        print(f"Error fetching TMDB data: {e}")
    return {"message": f"Error: {str(e)}", "poster_url": None}


async def format_tmdb_info(tmdb_type, movie_id, data):
    """
    Formats TMDb API response into a user-friendly message format.

    Args:
    - tmdb_type (str): The type of TMDb entity ('movie', 'tv', 'collection').
    - movie_id (int): The TMDb movie or TV show ID.
    - data (dict): The API response containing details of the entity.

    Returns:
    - str: Formatted string to be sent as a Telegram message using HTML.
    """
    cast_crew = await get_cast_and_crew(tmdb_type, movie_id)
    
    # Extract genres and convert them to hashtags
    genres = " ".join([f"#{genre['name'].replace(' ', '').replace('-', '').replace('&', '')}" for genre in data.get('genres', [])])

    if tmdb_type == 'movie':
        title = data.get('title', 'N/A')
        release_year = data.get('release_date', 'N/A')[:4]
        summary = truncate_overview(data.get('overview', 'N/A'))
        starring = ", ".join(cast_crew.get('starring', []))
        director = cast_crew.get('director', 'N/A')
        
        message = (
            f"<b>{title} ({release_year})  is now available.</b>\n\n"
            f"<b>Summary:</b> {summary}\n\n"
            f"<b>Starring:</b> {starring}\n\n"
            f"<b>Director:</b> {director}\n\n"
            f"{genres}"
        )
    
    elif tmdb_type == 'tv':
        title = data.get('name', 'N/A')
        release_year = data.get('first_air_date', 'N/A')[:4]
        summary = truncate_overview(data.get('overview', 'N/A'))
        starring = ", ".join(cast_crew.get('starring', []))
        
        message = (
            f"<b>{title} ({release_year})  is now available.</b>\n\n"
            f"<b>Summary:</b> {summary}\n\n"
            f"<b>Starring:</b> {starring}\n\n"
            f"{genres}"
        )
    
    elif tmdb_type == 'collection':
        title = data.get('name', 'N/A')
        summary = truncate_overview(data.get('overview', 'N/A'))
        
        message = (
            f"<b>{title} (Collection)  is now available.</b>\n\n"
            f"<b>Summary:</b> {summary}\n\n"
            f"{genres}"
        )
    else:
        message = "Unknown type. Unable to format information."
    
    return message


async def get_cast_and_crew(tmdb_type, movie_id):
    """
    Fetches the cast and crew details (starring actors and director) for a movie or TV show.
    
    Args:
    - tmdb_type (str): The type of TMDb entity ('movie', 'tv').
    - movie_id (int): The TMDb movie or TV show ID.

    Returns:
    - dict: A dictionary containing the starring actors and director.
    """
    cast_crew_url = f'https://api.themoviedb.org/3/{tmdb_type}/{movie_id}/credits?api_key={TMDB_API_KEY}&language=en-US'
    
    async with aiohttp.ClientSession() as session:
        async with session.get(cast_crew_url) as response:
            cast_crew_data = await response.json()

    # Get starring actors (first 3 cast members) and director
    starring = [member['name'] for member in cast_crew_data.get('cast', [])[:3]]
    director = next((member['name'] for member in cast_crew_data.get('crew', []) if member['job'] == 'Director'), 'N/A')

    return {"starring": starring, "director": director}


def truncate_overview(overview):
    """
    Truncate the overview if it exceeds the specified limit.

    Args:
    - overview (str): The overview text from the API.

    Returns:
    - str: Truncated overview with an ellipsis if it exceeds the limit.
    """
    MAX_OVERVIEW_LENGTH = 600  # Define your maximum character length for the summary
    if len(overview) > MAX_OVERVIEW_LENGTH:
        return overview[:MAX_OVERVIEW_LENGTH] + "..."
    return overview
