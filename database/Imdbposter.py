import re
import aiohttp
import asyncio
from io import BytesIO
from PIL import Image
from .Imdbposter import get_movie_details, fetch_high_quality_image as fetch_image
from imdb import Cinemagoer
from pyrogram import Client
import os

# Initialize IMDb
ia = Cinemagoer()

# Load Telegram Bot Config from info.py
from info import BOT_TOKEN, CHANNEL_ID

app = Client("imdb_bot", bot_token=BOT_TOKEN)

def list_to_str(lst):
    """Converts a list to a comma-separated string."""
    return ", ".join(map(str, lst)) if lst else "N/A"

async def fetch_high_quality_image(url):
    """Fetches the highest quality IMDb poster without compression."""
    if not IMAGE_FETCH:
        print("Image fetching is disabled.")
        return None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return BytesIO(await response.read())  # Keep original quality
                else:
                    print(f"Failed to fetch image: {response.status}")
    except aiohttp.ClientError as e:
        print(f"HTTP request error: {e}")
    return None

async def get_movie_details(query, id=False, file=None):
    """Fetches movie details, including a high-quality poster."""
    try:
        if not id:
            query = query.strip().lower()
            title = query
            year_match = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
            year = list_to_str(year_match[:1]) if year_match else None

            if not year and file:
                file_year_match = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
                year = list_to_str(file_year_match[:1]) if file_year_match else None

            movie_search = ia.search_movie(title.lower(), results=10)
            if not movie_search:
                return None

            filtered_movies = (
                [m for m in movie_search if str(m.get('year')) == year]
                if year else movie_search
            )

            filtered_movies = [
                m for m in filtered_movies if m.get('kind') in ['movie', 'tv series']
            ] or filtered_movies

            movieid = filtered_movies[0].movieID
        else:
            movieid = query

        movie = ia.get_movie(movieid)
        poster_url = movie.get('full-size cover url')

        details = {
            'title': movie.get('title'),
            'votes': movie.get('votes'),
            "aka": list_to_str(movie.get("akas")),
            "seasons": movie.get("number of seasons"),
            "box_office": movie.get('box office', {}).get('Cumulative Worldwide Gross', 'N/A'),
            'localized_title': movie.get('localized title'),
            'kind': movie.get("kind"),
            "imdb_id": f"tt{movie.get('imdbID')}",
            "cast": list_to_str(movie.get("cast")[:5]),  # Top 5 actors
            "runtime": list_to_str(movie.get("runtimes")),
            "countries": list_to_str(movie.get("countries")),
            "certificates": list_to_str(movie.get("certificates")),
            "languages": list_to_str(movie.get("languages")),
            "director": list_to_str(movie.get("director")),
            "writer": list_to_str(movie.get("writer")),
            "producer": list_to_str(movie.get("producer")),
            "composer": list_to_str(movie.get("composer")),
            "cinematographer": list_to_str(movie.get("cinematographer")),
            "music_team": list_to_str(movie.get("music department")),
            "distributors": list_to_str(movie.get("distributors")),
            'release_date': movie.get('original air date', movie.get('year', 'N/A')),
            'year': movie.get('year'),
            'genres': list_to_str(movie.get("genres")),
            'poster_url': poster_url,
            'plot': (movie.get('plot', ["N/A"])[0])[:1000] + "...",
            'rating': str(movie.get("rating")),
            'url': f'https://www.imdb.com/title/tt{movieid}'
        }

        return details
    except Exception as e:
        print(f"An error occurred in get_movie_details: {e}")
        return None

def generate_caption(details):
    """Generates a stylish caption for Telegram messages."""
    return (
        f"🎬 **{details['title']} ({details['year']})**\n"
        f"⭐ **Rating:** {details['rating']}/10\n"
        f"🎭 **Genres:** {details['genres']}\n"
        f"🎬 **Director:** {details['director']}\n"
        f"✍ **Writer:** {details['writer']}\n"
        f"👥 **Cast:** {details['cast']}\n"
        f"💰 **Box Office:** {details['box_office']}\n"
        f"📖 **Plot:** {details['plot']}\n\n"
        f"🔗 [IMDb Link]({details['url']})"
    )

async def send_to_telegram(details):
    """Sends movie details and highest-quality poster to Telegram channel."""
    async with app:
        caption = generate_caption(details)  # Generate stylish caption

        if details['poster_url']:
            image = await fetch_high_quality_image(details['poster_url'])
            if image:
                await app.send_photo(CHANNEL_ID, photo=image, caption=caption, parse_mode="markdown")
            else:
                await app.send_message(CHANNEL_ID, text=caption, parse_mode="markdown")  # Fallback to text only
        else:
            await app.send_message(CHANNEL_ID, text=caption, parse_mode="markdown")  # No poster found

async def main():
    query = "Inception 2010"  # Example movie
    details = await get_movie_details(query)
    if details:
        await send_to_telegram(details)
    else:
        print("Movie not found.")
