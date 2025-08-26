import asyncio
import logging
import os
from fastmcp import FastMCP 
import json
import re
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

mcp = FastMCP("MCP Server on Cloud Run", stateless_http=True)

load_dotenv(override=True)

# Database configuration
db_connection = None

DB_URL = os.getenv('DATABASE_URL') # "postgresql://postgres.cvzlylxhvthjvmjuluqe:0emrypuED2Z1f43c@aws-0-us-east-1.pooler.supabase.com:5432/postgres" # "postgresql://postgres:Mc1jG1jFrMEKXkws@db.cvzlylxhvthjvmjuluqe.supabase.co:5432/postgres" # "postgresql://postgres.cvzlylxhvthjvmjuluqe:Mc1jG1jFrMEKXkws@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

# TMDB API Configuration
TMDB_CONFIG = {
    'base_url': 'https://api.themoviedb.org/3',
    'api_key': os.getenv('TMDB_API_KEY'),
    'account_id': os.getenv('TMDB_ACCOUNT_ID'),
    'session_id': os.getenv('TMDB_SESSION_ID'),
    'headers': {
        'Content-Type': 'application/json'
    },
    # Endpoint mapping with descriptions
    'endpoints': {
        # Search endpoints
        'search_movie': {
            'url': '/search/movie',
            'method': 'GET',
            'description': 'Search for movies by title',
            'keywords': ['search', 'find', 'look for', 'movie', 'film'],
            'required_params': ['query']
        },
        'search_tv': {
            'url': '/search/tv',
            'method': 'GET',
            'description': 'Search for TV shows by title',
            'keywords': ['search', 'find', 'look for', 'tv', 'show', 'series'],
            'required_params': ['query']
        },
        'search_person': {
            'url': '/search/person',
            'method': 'GET',
            'description': 'Search for people (actors, directors)',
            'keywords': ['search', 'find', 'look for', 'actor', 'actress', 'director', 'person'],
            'required_params': ['query']
        },
        
        # Movie endpoints
        'movie_details': {
            'url': '/movie/{id}',
            'method': 'GET',
            'description': 'Get detailed information about a movie',
            'keywords': ['details', 'info', 'information', 'about', 'movie details'],
            'required_params': ['id']
        },
        'movie_credits': {
            'url': '/movie/{id}/credits',
            'method': 'GET',
            'description': 'Get cast and crew for a movie',
            'keywords': ['cast', 'crew', 'actors', 'director', 'credits', 'who is in'],
            'required_params': ['id']
        },
        'movie_reviews': {
            'url': '/movie/{id}/reviews',
            'method': 'GET',
            'description': 'Get reviews for a movie',
            'keywords': ['reviews', 'review', 'critics', 'opinions'],
            'required_params': ['id']
        },
        'movie_similar': {
            'url': '/movie/{id}/similar',
            'method': 'GET',
            'description': 'Get similar movies',
            'keywords': ['similar', 'like', 'recommendations', 'suggestions'],
            'required_params': ['id']
        },
        
        # TV endpoints
        'tv_details': {
            'url': '/tv/{id}',
            'method': 'GET',
            'description': 'Get detailed information about a TV show',
            'keywords': ['details', 'info', 'information', 'about', 'tv details', 'show details'],
            'required_params': ['id']
        },
        'tv_credits': {
            'url': '/tv/{id}/credits',
            'method': 'GET',
            'description': 'Get cast and crew for a TV show',
            'keywords': ['cast', 'crew', 'actors', 'director', 'credits', 'who is in'],
            'required_params': ['id']
        },
        
        # Lists and collections
        'popular_movies': {
            'url': '/movie/popular',
            'method': 'GET',
            'description': 'Get popular movies',
            'keywords': ['popular', 'trending', 'top', 'best', 'popular movies'],
            'required_params': []
        },
        'top_rated_movies': {
            'url': '/movie/top_rated',
            'method': 'GET',
            'description': 'Get top rated movies',
            'keywords': ['top rated', 'best rated', 'highest rated', 'top movies'],
            'required_params': []
        },
        'upcoming_movies': {
            'url': '/movie/upcoming',
            'method': 'GET',
            'description': 'Get upcoming movies',
            'keywords': ['upcoming', 'coming soon', 'new movies', 'releases'],
            'required_params': []
        },
        'now_playing_movies': {
            'url': '/movie/now_playing',
            'method': 'GET',
            'description': 'Get movies currently in theaters',
            'keywords': ['now playing', 'in theaters', 'current movies', 'cinema'],
            'required_params': []
        },
        'popular_tv': {
            'url': '/tv/popular',
            'method': 'GET',
            'description': 'Get popular TV shows',
            'keywords': ['popular', 'trending', 'top', 'best', 'popular shows', 'popular tv'],
            'required_params': []
        },
        'top_rated_tv': {
            'url': '/tv/top_rated',
            'method': 'GET',
            'description': 'Get top rated TV shows',
            'keywords': ['top rated', 'best rated', 'highest rated', 'top shows', 'top tv'],
            'required_params': []
        },
        'on_the_air_tv': {
            'url': '/tv/on_the_air',
            'method': 'GET',
            'description': 'Get TV shows currently on the air',
            'keywords': ['on the air', 'currently airing', 'airing now', 'current shows'],
            'required_params': []
        },
        
        # Account endpoints
        'add_to_watchlist': {
            'url': '/account/{account_id}/watchlist',
            'method': 'POST',
            'description': 'Add movie or TV show to watchlist',
            'keywords': ['add to watchlist', 'add watchlist', 'save to watchlist', 'watchlist add'],
            'required_params': ['media_type', 'media_id']
        },
        'get_watchlist_movies': {
            'url': '/account/{account_id}/watchlist/movies',
            'method': 'GET',
            'description': 'Get movies in watchlist',
            'keywords': ['watchlist movies', 'my watchlist', 'saved movies', 'watchlist'],
            'required_params': []
        },
        'get_watchlist_tv': {
            'url': '/account/{account_id}/watchlist/tv',
            'method': 'GET',
            'description': 'Get TV shows in watchlist',
            'keywords': ['watchlist tv', 'watchlist shows', 'saved shows', 'tv watchlist'],
            'required_params': []
        },
        'add_favorite': {
            'url': '/account/{account_id}/favorite',
            'method': 'POST',
            'description': 'Add movie or TV show to favorites',
            'keywords': ['add to favorites', 'favorite', 'like', 'save favorite'],
            'required_params': ['media_type', 'media_id']
        },
        'get_favorite_movies': {
            'url': '/account/{account_id}/favorite/movies',
            'method': 'GET',
            'description': 'Get favorite movies',
            'keywords': ['favorite movies', 'my favorites', 'liked movies'],
            'required_params': []
        },
        'get_favorite_tv': {
            'url': '/account/{account_id}/favorite/tv',
            'method': 'GET',
            'description': 'Get favorite TV shows',
            'keywords': ['favorite tv', 'favorite shows', 'liked shows'],
            'required_params': []
        },
        'add_rating': {
            'url': '/movie/{id}/rating',
            'method': 'POST',
            'description': 'Rate a movie',
            'keywords': ['rate', 'rating', 'give rating', 'score'],
            'required_params': ['id', 'value']
        },
        'get_rated_movies': {
            'url': '/account/{account_id}/rated/movies',
            'method': 'GET',
            'description': 'Get rated movies',
            'keywords': ['rated movies', 'my ratings', 'movies I rated'],
            'required_params': []
        },
        
        # Person endpoints
        'person_details': {
            'url': '/person/{id}',
            'method': 'GET',
            'description': 'Get person details',
            'keywords': ['person details', 'actor details', 'director details', 'about'],
            'required_params': ['id']
        },
        'person_movie_credits': {
            'url': '/person/{id}/movie_credits',
            'method': 'GET',
            'description': 'Get movies a person has worked on',
            'keywords': ['movies', 'filmography', 'works', 'appearances'],
            'required_params': ['id']
        },
        'person_tv_credits': {
            'url': '/person/{id}/tv_credits',
            'method': 'GET',
            'description': 'Get TV shows a person has worked on',
            'keywords': ['tv shows', 'television', 'series', 'tv appearances'],
            'required_params': ['id']
        },
        
        # Genre endpoints
        'movie_genres': {
            'url': '/genre/movie/list',
            'method': 'GET',
            'description': 'Get movie genres',
            'keywords': ['genres', 'movie genres', 'categories'],
            'required_params': []
        },
        'tv_genres': {
            'url': '/genre/tv/list',
            'method': 'GET',
            'description': 'Get TV genres',
            'keywords': ['tv genres', 'show genres', 'tv categories'],
            'required_params': []
        },
        
        # Discover endpoints
        'discover_movies': {
            'url': '/discover/movie',
            'method': 'GET',
            'description': 'Discover movies with filters',
            'keywords': ['discover', 'find movies', 'browse movies', 'explore'],
            'required_params': []
        },
        'discover_tv': {
            'url': '/discover/tv',
            'method': 'GET',
            'description': 'Discover TV shows with filters',
            'keywords': ['discover', 'find shows', 'browse shows', 'explore tv'],
            'required_params': []
        }
    }
}

@mcp.tool()
def add(a: int, b: int) -> int:
    """Use this to add two numbers together.

    Args:
        a: The first number.
        b: The second number.

    Returns:
        The sum of the two numbers.
    """
    logger.info(f">>> 🛠️ Tool: 'add' called with numbers '{a}' and '{b}'")
    return a + b

@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Use this to subtract two numbers.

    Args:
        a: The first number.
        b: The second number.

    Returns:
        The difference of the two numbers.
    """
    logger.info(f">>> 🛠️ Tool: 'subtract' called with numbers '{a}' and '{b}'")
    return a - b

@mcp.tool()
def query_demo_db(sql: str) -> str:
    """Execute SQL queries against the Demo PostgreSQL database"""
    if not sql:
        raise ValueError("SQL query is required")
    
    try:
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(sql)
        
        if sql.strip().upper().startswith("SELECT"):
            results = cursor.fetchall()
            json_results = []
            for row in results:
                json_results.append(dict(row))
            
            return json.dumps(json_results, indent=2, default=str)
        else:
            db_connection.commit()
            return f"Query executed successfully. Rows affected: {cursor.rowcount}"
    except Exception as e:
        db_connection.rollback()
        raise e
    '''finally:
        cursor.close()'''


@mcp.tool()
def tmdb_intelligent_call(request: str) -> str:
    """Intelligently determine and call the appropriate TMDB API endpoint based on your request. Examples: 'Search for Inception', 'Add The Dark Knight to my watchlist', 'Get popular movies', 'Find movies by Christopher Nolan', 'Get cast of Breaking Bad', 'Rate The Shawshank Redemption 5 stars', 'Show my watchlist', 'Get movie details for Interstellar'"""
    request_text = request.lower()
    
    # Step 1: Find the best matching endpoint
    best_endpoint = _find_best_endpoint(request_text)
    
    if not best_endpoint:
        return f"Could not determine appropriate TMDB endpoint for: {request}\n\nAvailable operations:\n- Search for movies/shows/people\n- Get details, cast, reviews, similar content\n- Get popular, top rated, upcoming content\n- Manage watchlist and favorites\n- Rate movies/shows\n- Discover content with filters"
    
    # Step 2: Extract parameters
    params = _extract_parameters(request_text, best_endpoint)
    
    # Step 3: Build URL and make request
    return _execute_tmdb_request(best_endpoint, params)

@mcp.tool()
def http_get(url: str, headers: Optional[Dict[str, str]] = None) -> str:
    """Make HTTP GET requests to any external API"""
    if headers is None:
        headers = {}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
            return content
    except Exception as e:
        raise Exception(f"HTTP GET request failed: {e}")

'''def connect_db():
    """Establish database connection"""
    global db_connection
    try:
        db_connection = psycopg2.connect(**DB_CONFIG)
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
'''

# Connect to postgres database
def connect_db() -> psycopg2.extensions.connection:
    """Create database connection with appropriate SSL settings."""
    global db_connection
    try:
        conn_params = psycopg2.extensions.parse_dsn(DB_URL)
        db_connection = psycopg2.connect(**conn_params)
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def disconnect_db():
    """Close database connection"""
    global db_connection
    if db_connection:
        db_connection.close()
        logger.info("Database connection closed")



def _find_best_endpoint(request_text: str) -> Optional[str]:
    """Find the best matching TMDB endpoint based on request text"""
    best_match = None
    best_score = 0
    
    for endpoint_name, endpoint_info in TMDB_CONFIG['endpoints'].items():
        score = 0
        
        # Check keyword matches
        for keyword in endpoint_info['keywords']:
            if keyword in request_text:
                score += 1
        
        # Bonus for exact matches
        if any(keyword in request_text for keyword in endpoint_info['keywords']):
            score += 0.5
        
        # Specific patterns for certain endpoints
        if endpoint_name == 'add_to_watchlist' and any(word in request_text for word in ['add', 'save', 'put']):
            score += 2
        
        if endpoint_name == 'add_rating' and any(word in request_text for word in ['rate', 'rating', 'score']):
            score += 2
        
        if endpoint_name in ['popular_movies', 'popular_tv'] and 'popular' in request_text:
            score += 2
        
        if endpoint_name in ['top_rated_movies', 'top_rated_tv'] and any(word in request_text for word in ['top rated', 'best', 'highest']):
            score += 2
        
        if endpoint_name in ['upcoming_movies', 'now_playing_movies'] and any(word in request_text for word in ['upcoming', 'coming soon', 'new', 'now playing']):
            score += 2
        
        if endpoint_name in ['get_watchlist_movies', 'get_watchlist_tv'] and 'watchlist' in request_text and not any(word in request_text for word in ['add', 'save', 'put']):
            score += 2
        
        if endpoint_name in ['get_favorite_movies', 'get_favorite_tv'] and any(word in request_text for word in ['favorite', 'favourites', 'liked']):
            score += 2
        
        if score > best_score:
            best_score = score
            best_match = endpoint_name
    
    return best_match

def _extract_parameters(request_text: str, endpoint_name: str) -> Dict[str, Any]:
    """Extract parameters from request text for the given endpoint"""
    params = {}
    endpoint_info = TMDB_CONFIG['endpoints'][endpoint_name]
    
    # Extract title/query for search endpoints
    if 'search' in endpoint_name:
        title_match = re.search(r'(?:search|find|look for|get)\s+(?:for\s+)?["\']?([^"\']+)["\']?', request_text)
        if title_match:
            params['query'] = title_match.group(1).strip()
    
    # Extract title for other endpoints that need it
    elif endpoint_name in ['movie_details', 'tv_details', 'movie_credits', 'tv_credits', 'add_to_watchlist', 'add_favorite', 'add_rating']:
        title_match = re.search(r'(?:for|about|get|find|add|rate)\s+["\']?([^"\']+)["\']?', request_text)
        if title_match:
            params['title'] = title_match.group(1).strip()
    
    # Extract rating value
    if endpoint_name == 'add_rating':
        rating_match = re.search(r'(\d+)\s*(?:stars?|rating|score)', request_text)
        if rating_match:
            params['value'] = float(rating_match.group(1))
        else:
            # Default rating if not specified
            params['value'] = 5.0
    
    # Extract media type for watchlist/favorites
    if endpoint_name in ['add_to_watchlist', 'add_favorite']:
        if any(word in request_text for word in ['tv', 'show', 'series']):
            params['media_type'] = 'tv'
        else:
            params['media_type'] = 'movie'
    
    # Extract person name for person endpoints
    if endpoint_name in ['person_details', 'person_movie_credits', 'person_tv_credits']:
        person_match = re.search(r'(?:for|about|get)\s+["\']?([^"\']+)["\']?', request_text)
        if person_match:
            params['person_name'] = person_match.group(1).strip()
    
    # Extract season number for TV season endpoints
    if endpoint_name == 'tv_season_details':
        season_match = re.search(r'season\s+(\d+)', request_text)
        if season_match:
            params['season_number'] = int(season_match.group(1))
    
    return params

def _execute_tmdb_request(endpoint_name: str, params: Dict[str, Any]) -> str:
    """Execute the TMDB API request"""
    endpoint_info = TMDB_CONFIG['endpoints'][endpoint_name]
    
    try:
        # Handle special cases that require searching first
        if endpoint_name in ['movie_details', 'tv_details', 'movie_credits', 'tv_credits', 'add_to_watchlist', 'add_favorite', 'add_rating'] and 'title' in params:
            # Search for the title first to get the ID
            search_result = _search_for_title(params['title'], endpoint_name)
            if not search_result:
                return f"Could not find '{params['title']}' in TMDB database"
            params['id'] = search_result['id']
        
        elif endpoint_name in ['person_details', 'person_movie_credits', 'person_tv_credits'] and 'person_name' in params:
            # Search for the person first
            search_result = _search_for_person(params['person_name'])
            if not search_result:
                return f"Could not find person '{params['person_name']}' in TMDB database"
            params['id'] = search_result['id']
        
        # Build the URL
        url = _build_tmdb_url(endpoint_name, params)
        
        # Make the request
        if endpoint_info['method'] == 'GET':
            return _http_get_internal(url, TMDB_CONFIG['headers'])
        else:  # POST
            data = _build_post_data(endpoint_name, params)
            return _http_post_internal(url, data, TMDB_CONFIG['headers'])
            
    except Exception as e:
        return f"Error executing TMDB request: {str(e)}"

def _search_for_title(title: str, endpoint_name: str) -> Optional[Dict[str, Any]]:
    """Search for a title and return the first result"""
    # Determine if we're looking for a movie or TV show
    if 'tv' in endpoint_name or any(word in title.lower() for word in ['series', 'show', 'tv']):
        search_url = f"{TMDB_CONFIG['base_url']}{TMDB_CONFIG['endpoints']['search_tv']['url']}?query={urllib.parse.quote(title)}"
    else:
        search_url = f"{TMDB_CONFIG['base_url']}{TMDB_CONFIG['endpoints']['search_movie']['url']}?query={urllib.parse.quote(title)}"
    
    try:
        response = _http_get_internal(search_url, TMDB_CONFIG['headers'])
        data = json.loads(response)
        
        if data.get('results') and len(data['results']) > 0:
            return data['results'][0]
    except Exception as e:
        logger.error(f"Search failed: {e}")
    
    return None

def _search_for_person(person_name: str) -> Optional[Dict[str, Any]]:
    """Search for a person and return the first result"""
    search_url = f"{TMDB_CONFIG['base_url']}{TMDB_CONFIG['endpoints']['search_person']['url']}?query={urllib.parse.quote(person_name)}"
    
    try:
        response = _http_get_internal(search_url, TMDB_CONFIG['headers'])
        data = json.loads(response)
        
        if data.get('results') and len(data['results']) > 0:
            return data['results'][0]
    except Exception as e:
        logger.error(f"Person search failed: {e}")
    
    return None

def _build_tmdb_url(endpoint_name: str, params: Dict[str, Any]) -> str:
    """Build the TMDB URL for the given endpoint and parameters"""
    endpoint_info = TMDB_CONFIG['endpoints'][endpoint_name]
    url = f"{TMDB_CONFIG['base_url']}{endpoint_info['url']}"
    
    # Replace path parameters
    if 'id' in params:
        url = url.replace('{id}', str(params['id']))
    
    if 'account_id' in endpoint_info['url']:
        url = url.replace('{account_id}', TMDB_CONFIG['account_id'])
    
    if 'season_number' in params:
        url = url.replace('{season_number}', str(params['season_number']))
    
    # Add query parameters for GET requests
    if endpoint_info['method'] == 'GET':
        query_params = []
        
        # Always add API key as query parameter
        query_params.append(f"api_key={TMDB_CONFIG['api_key']}")
        
        if 'query' in params:
            query_params.append(f"query={urllib.parse.quote(params['query'])}")
        
        if 'page' in params:
            query_params.append(f"page={params['page']}")
        
        if query_params:
            url += '?' + '&'.join(query_params)
    
    return url

def _build_post_data(endpoint_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Build POST data for the given endpoint"""
    if endpoint_name == 'add_to_watchlist':
        return {
            "media_type": params['media_type'],
            "media_id": params['id'],
            "watchlist": True
        }
    elif endpoint_name == 'add_favorite':
        return {
            "media_type": params['media_type'],
            "media_id": params['id'],
            "favorite": True
        }
    elif endpoint_name == 'add_rating':
        return {
            "value": params['value']
        }
    
    return {}

def _http_get_internal(url: str, headers: Dict[str, str]) -> str:
    """Internal HTTP GET method"""
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
            return content
    except Exception as e:
        raise Exception(f"HTTP GET request failed: {e}")

def _http_post_internal(url: str, data: Dict[str, Any], headers: Dict[str, str]) -> str:
    """Internal HTTP POST method"""
    try:
        # For POST requests, we need a session ID for account operations
        # Check if we have a session ID, otherwise return an error
        if not TMDB_CONFIG['session_id']:
            return "Error: Session ID is required for POST requests. Please add TMDB_SESSION_ID to your .env file. You can get a session ID by following the authentication flow at https://www.themoviedb.org/settings/api"
        
        # Add session ID to URL for POST requests
        separator = '&' if '?' in url else '?'
        url_with_session = f"{url}{separator}session_id={TMDB_CONFIG['session_id']}"
        
        data_bytes = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
        
        req = urllib.request.Request(url_with_session, data=data_bytes, headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
            return content
    except Exception as e:
        raise Exception(f"HTTP POST request failed: {e}")




if __name__ == "__main__":
    connect_db()
    logger.info(f"🚀 MCP server started on port {os.getenv('PORT', 8080)}")
    # Could also use 'sse' transport, host="0.0.0.0" required for Cloud Run.
    asyncio.run(
        mcp.run_async(
            transport="streamable-http",
            host="0.0.0.0",
            port=os.getenv("PORT", 8080),
        )
    )
    # disconnect_db()