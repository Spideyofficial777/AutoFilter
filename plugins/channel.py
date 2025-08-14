from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import CHANNELS, MOVIE_UPDATE_CHANNEL, ADMINS, LOG_CHANNEL
from database.ia_filterdb import save_file, unpack_new_file_id
from utils import get_poster, temp
import re
from database.users_chats_db import db
from Script import script  

processed_movies = set()
media_filter = filters.document | filters.video

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    bot_id = bot.me.id
    media = getattr(message, message.media.value, None)
    if media.mime_type in ['video/mp4', 'video/x-matroska']: 
        media.file_type = message.media.value
        media.caption = message.caption
        success_sts = await save_file(media)
        if success_sts == 'suc' and await db.get_send_movie_update_status(bot_id):
            file_id, file_ref = unpack_new_file_id(media.file_id)
            await send_movie_updates(bot, file_name=media.file_name, caption=media.caption, file_id=file_id)

async def get_imdb(file_name):
    imdb_file_name = await movie_name_format(file_name)
    imdb = await get_poster(imdb_file_name)
    print(f"IMDb Data for {imdb_file_name}: {imdb}")

    if imdb:
        poster = imdb.get('poster')
        rating = imdb.get('rating', 'N/A')  
        genres = imdb.get('genres', 'Unknown')  
        votes = imdb.get('votes', 'N/A')
        description = imdb.get('plot') or imdb.get('description') or "No description available."

        runtime = imdb.get('runtime', 'Unknown')  
        director = imdb.get('director', 'Unknown')  
        actors = ", ".join(imdb.get('actors', ['Unknown']))  
        release_date = imdb.get('release_date', 'Unknown')  
        box_office = imdb.get('box_office', 'Unknown')  
        country = imdb.get('country', 'Unknown')

        return poster, rating, genres, votes, description, runtime, director, actors, release_date, box_office, country  
    return None, "N/A", "Unknown", "N/A", "No description available.", "Unknown", "Unknown", "Unknown", "Unknown", "Unknown", "Unknown"

async def movie_name_format(file_name):
    if not file_name:
        return "Unknown"
    
    filename = re.sub(r'http\S+', '', re.sub(r'@\w+|#\w+', '', file_name)
                      .replace('_', ' ')
                      .replace('[', '').replace(']', '')
                      .replace('(', '').replace(')', '')
                      .replace('{', '').replace('}', '')
                      .replace('.', ' ').replace('@', '')
                      .replace(':', '').replace(';', '')
                      .replace("'", '').replace('-', '')
                      .replace('!', '')).strip()
    return filename

async def check_qualities(text, qualities: list):
    quality = []
    for q in qualities:
        if q in text:
            quality.append(q)
    quality = ", ".join(quality)
    return quality[:-2] if quality.endswith(", ") else quality

async def send_movie_updates(bot, file_name, caption, file_id):
    try:
        if not file_name:
            print("Error: file_name is None!")
            return
        
        year_match = re.search(r"\b(19|20)\d{2}\b", caption) if caption else None
        year = year_match.group(0) if year_match else None      
        pattern = r"(?i)(?:s|season)0*(\d{1,2})"
        season = re.search(pattern, caption) if caption else None
        if not season:
            season = re.search(pattern, file_name) if file_name else None 

        if file_name and year and year in file_name:
            file_name = file_name[:file_name.find(year) + 4]

        if file_name and season and season.group(1) in file_name:
            file_name = file_name[:file_name.find(season.group(1)) + 1]

        qualities = ["ORG", "org", "hdcam", "HDCAM", "HQ", "hq", "HDRip", "hdrip", 
                     "camrip", "WEB-DL", "CAMRip", "hdtc", "predvd", "DVDscr", "dvdscr", 
                     "dvdrip", "dvdscr", "HDTC", "dvdscreen", "HDTS", "hdts"]
        quality = await check_qualities(caption, qualities) if caption else "HDRip"

        language = ""
        nb_languages = ["Hindi", "Bengali", "English", "Marathi", "Tamil", "Telugu", 
                        "Malayalam", "Kannada", "Punjabi", "Gujrati", "Korean", "Japanese", 
                        "Bhojpuri", "Dual", "Multi"]    
        for lang in nb_languages:
            if caption and lang.lower() in caption.lower():
                language += f"{lang}, "
        language = language.strip(", ") or "Not Idea"

        movie_name = await movie_name_format(file_name)    

        if movie_name in processed_movies and "movie" not in movie_name.lower():
            return 
        processed_movies.add(movie_name)        
        
        poster_url, rating, genres, votes, description, runtime, director, actors, release_date, box_office, country = await get_imdb(movie_name)

        caption_message = script.MOVIES_UPDATE_TXT.format(
            title=movie_name,
            genres=genres,
            rating=rating,
            votes=votes,
            description=description,
            runtime=runtime,
            director=director,
            actors=actors,
            release_date=release_date,
            box_office=box_office,
            country=country
        )

        search_movie = movie_name.replace(" ", '-')
        movie_update_channel = await db.movies_update_channel_id()    

        btn = [[
            InlineKeyboardButton('📂 ɢᴇᴛ ғɪʟᴇ 📂', url=f'https://telegram.me/{temp.U_NAME}?start={file_id}')
        ],[
            InlineKeyboardButton('♻️ ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ ♻️', url='https://t.me/spideyofficial_777/12')
        ]]
        reply_markup = InlineKeyboardMarkup(btn)

        if poster_url:
            await bot.send_photo(movie_update_channel if movie_update_channel else MOVIE_UPDATE_CHANNEL, 
                                 photo=poster_url, caption=caption_message, reply_markup=reply_markup)
        else:
            no_poster = "https://telegra.ph/file/88d845b4f8a024a71465d.jpg"
            await bot.send_photo(movie_update_channel if movie_update_channel else MOVIE_UPDATE_CHANNEL, 
                                 photo=no_poster, caption=caption_message, reply_markup=reply_markup)  
    except Exception as e:
        print('Failed to send movie update. Error - ', e)
        await bot.send_message(LOG_CHANNEL, f'Failed to send movie update. Error - {e}')
