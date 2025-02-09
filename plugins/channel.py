from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import CHANNELS, MOVIE_UPDATE_CHANNEL, ADMINS, LOG_CHANNEL
from database.ia_filterdb import save_file, unpack_new_file_id
from utils import get_poster, temp
import re
from database.users_chats_db import db

processed_movies = set()
media_filter = filters.document | filters.video | filters.audio  # Audio support added

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    """Media Handler"""
    bot_id = bot.me.id

    # Identify media type
    media = None
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media:
            break
    if not media:
        return

    media.file_type = file_type
    media.caption = message.caption

    success_sts = await save_file(media)
    if success_sts == 'suc' and await db.get_send_movie_update_status(bot_id):
        file_id, file_ref = unpack_new_file_id(media.file_id)
        await send_movie_updates(bot, file_name=media.file_name, caption=media.caption, file_id=file_id)

async def get_imdb(file_name):
    """Fetch IMDb poster, rating, and description."""
    imdb_file_name = await movie_name_format(file_name)
    imdb = await get_poster(imdb_file_name)
    if imdb:
        return imdb.get('poster'), imdb.get('rating', 'N/A'), imdb.get('description', 'No description available.')
    return None, 'N/A', 'No description available.'

async def movie_name_format(file_name):
    """Format the movie name properly by removing unwanted characters."""
    return re.sub(r'http\S+|@\w+|#\w+', '', file_name).replace('_', ' ').replace('.', ' ').strip()

async def check_qualities(text, qualities):
    """Check available qualities in the text."""
    return ", ".join([q for q in qualities if q in text]) or "HDRip"

async def send_movie_updates(bot, file_name, caption, file_id):
    """Send movie updates to the channel."""
    try:
        year_match = re.search(r"\b(19|20)\d{2}\b", caption)
        year = year_match.group(0) if year_match else None
        season_match = re.search(r"(?i)(?:s|season)0*(\d{1,2})", caption) or re.search(r"(?i)(?:s|season)0*(\d{1,2})", file_name)

        if year:
            file_name = file_name[:file_name.find(year) + 4]
        elif season_match:
            file_name = file_name[:file_name.find(season_match.group(1)) + 1]

        qualities = ["ORG", "org", "hdcam", "HDCAM", "HQ", "hq", "HDRip", "hdrip",
                     "camrip", "WEB-DL", "CAMRip", "hdtc", "predvd", "DVDscr",
                     "dvdscr", "dvdrip", "HDTC", "dvdscreen", "HDTS", "hdts"]
        quality = await check_qualities(caption, qualities)

        languages = ["Hindi", "Bengali", "English", "Marathi", "Tamil", "Telugu", "Malayalam",
                     "Kannada", "Punjabi", "Gujarati", "Korean", "Japanese", "Bhojpuri", "Dual", "Multi"]
        language = ", ".join([lang for lang in languages if lang.lower() in caption.lower()]) or "Not Sure"

        movie_name = await movie_name_format(file_name)
        if movie_name in processed_movies:
            return
        processed_movies.add(movie_name)

        poster_url, rating, description = await get_imdb(movie_name)

        caption_message = f"""<b>#New_File_Added ✅
🍿 Title: {movie_name}
🧠 Language: {language}
⚠️ Quality: {quality}
⭐ Rating: {rating} / 10
📖 Description: {description}</b>"""

        search_movie = movie_name.replace(" ", '-')
        movie_update_channel = await db.movies_update_channel_id()
        btn = [[
            InlineKeyboardButton('📂 Get File 📂', url=f'https://telegram.me/{temp.U_NAME}?start=getfile-{search_movie}')
        ], [
            InlineKeyboardButton('♻️ How to Download ♻️', url=f'https://t.me/spideyofficial_777/12')
        ]]
        reply_markup = InlineKeyboardMarkup(btn)

        await bot.send_photo(
            movie_update_channel if movie_update_channel else MOVIE_UPDATE_CHANNEL,
            photo=poster_url or "https://telegra.ph/file/88d845b4f8a024a71465d.jpg",
            caption=caption_message,
            reply_markup=reply_markup
        )

    except Exception as e:
        print(f'Error sending movie update: {e}')
        await bot.send_message(LOG_CHANNEL, f'Error sending movie update: {e}')
