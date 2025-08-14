import os
import re
from datetime import timedelta
from pymediainfo import MediaInfo
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import CHANNELS, MOVIE_UPDATE_CHANNEL, ADMINS, LOG_CHANNEL
from database.ia_filterdb import save_file, unpack_new_file_id
from database.users_chats_db import db
from utils import temp
from Script import script

processed_files = set()

# Adult content keywords (case insensitive)
ADULT_KEYWORDS = [
    'xxx', 'porn', 'sex', 'fuck', 'adult', '18+', 'nsfw', 'hentai',
    'blowjob', 'cum', 'cock', 'dick', 'pussy', 'ass', 'boobs', 'tits',
    'slut', 'whore', 'bdsm', 'anal', 'milf', 'horny', 'erotic', 'nude'
]

# Supported media types
media_filter = filters.document | filters.video | filters.audio | filters.photo

def is_adult_content(filename, caption=None):
    """Check if content might be adult/pornographic"""
    if not filename:
        filename = ""
    if caption:
        text = f"{filename.lower()} {caption.lower()}"
    else:
        text = filename.lower()
    
    # Check for adult keywords
    for keyword in ADULT_KEYWORDS:
        if re.search(rf'\b{keyword}\b', text):
            return True
    
    # Check common porn file patterns
    porn_patterns = [
        r'\b[a-z]{3,5}-?\d{3,5}\b',  # Common porn video codes (like abc-123)
        r'\b(?:brazzers|realitykings|naughtyamerica|bangbros)\b'  # Common porn studios
    ]
    
    for pattern in porn_patterns:
        if re.search(pattern, text):
            return True
    
    return False

def format_size(size_bytes):
    """Convert file size to human-readable format"""
    if size_bytes is None:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def format_duration(seconds):
    """Convert duration to HH:MM:SS format"""
    if seconds is None:
        return "Unknown"
    return str(timedelta(seconds=int(seconds)))

def extract_metadata(file_path):
    """Extract metadata using MediaInfo library"""
    media_info = MediaInfo.parse(file_path)
    data = {
        "general": {},
        "video": [],
        "audio": [],
        "image": {},
        "text": []
    }

    for track in media_info.tracks:
        if track.track_type == "General":
            data["general"].update({
                "format": track.format,
                "file_size": format_size(track.file_size),
                "duration": format_duration(track.duration/1000),
                "overall_bit_rate": f"{track.overall_bit_rate/1000:.2f} kbps" if track.overall_bit_rate else "Unknown",
                "file_name": track.file_name,
                "file_extension": track.file_extension,
                "mime_type": track.internet_media_type
            })
        elif track.track_type == "Video":
            video_data = {
                "format": track.format,
                "codec": track.codec_id or track.format,
                "duration": format_duration(track.duration/1000),
                "bit_rate": f"{track.bit_rate/1000:.2f} kbps" if track.bit_rate else "Unknown",
                "width": f"{track.width} px" if track.width else "Unknown",
                "height": f"{track.height} px" if track.height else "Unknown",
                "aspect_ratio": track.display_aspect_ratio or "Unknown",
                "frame_rate": f"{track.frame_rate} fps" if track.frame_rate else "Unknown"
            }
            data["video"].append(video_data)
        elif track.track_type == "Audio":
            audio_data = {
                "format": track.format,
                "codec": track.codec_id or track.format,
                "duration": format_duration(track.duration/1000),
                "bit_rate": f"{track.bit_rate/1000:.2f} kbps" if track.bit_rate else "Unknown",
                "channels": f"{track.channel_s} channels" if track.channel_s else "Unknown",
                "sampling_rate": f"{track.sampling_rate/1000:.2f} kHz" if track.sampling_rate else "Unknown",
                "language": track.language or "Unknown"
            }
            data["audio"].append(audio_data)
        elif track.track_type == "Image":
            data["image"].update({
                "format": track.format,
                "width": f"{track.width} px" if track.width else "Unknown",
                "height": f"{track.height} px" if track.height else "Unknown",
                "color_space": track.color_space or "Unknown",
                "compression": track.compression_mode or "Unknown"
            })
        elif track.track_type == "Text":
            text_data = {
                "format": track.format,
                "language": track.language or "Unknown",
                "subtitle_type": "Forced" if track.forced == "Yes" else "Normal"
            }
            data["text"].append(text_data)
    
    return data

def generate_caption(file_name, metadata, is_adult=False):
    """Generate caption from metadata"""
    # Add adult content warning if detected
    adult_tag = "🔞 <b>[ADULT CONTENT]</b> 🔞\n\n" if is_adult else ""
    
    caption = f"{adult_tag}📁 <b>File Name:</b> <code>{file_name}</code>\n\n"
    
    # General info
    general = metadata.get("general", {})
    caption += "📦 <b>General Information:</b>\n"
    caption += f"• Format: <code>{general.get('format', 'Unknown')}</code>\n"
    caption += f"• Size: <code>{general.get('file_size', 'Unknown')}</code>\n"
    caption += f"• Duration: <code>{general.get('duration', 'Unknown')}</code>\n"
    caption += f"• Bit Rate: <code>{general.get('overall_bit_rate', 'Unknown')}</code>\n"
    caption += f"• MIME Type: <code>{general.get('mime_type', 'Unknown')}</code>\n\n"
    
    # Video info
    if metadata.get("video"):
        caption += "🎥 <b>Video Track(s):</b>\n"
        for i, video in enumerate(metadata["video"], 1):
            caption += f"<b>Track {i}:</b>\n"
            caption += f"• Codec: <code>{video.get('codec', 'Unknown')}</code>\n"
            caption += f"• Resolution: <code>{video.get('width')} × {video.get('height')}</code>\n"
            caption += f"• Aspect Ratio: <code>{video.get('aspect_ratio', 'Unknown')}</code>\n"
            caption += f"• Frame Rate: <code>{video.get('frame_rate', 'Unknown')}</code>\n"
            caption += f"• Bit Rate: <code>{video.get('bit_rate', 'Unknown')}</code>\n\n"
    
    # Audio info
    if metadata.get("audio"):
        caption += "🔊 <b>Audio Track(s):</b>\n"
        for i, audio in enumerate(metadata["audio"], 1):
            caption += f"<b>Track {i}:</b>\n"
            caption += f"• Codec: <code>{audio.get('codec', 'Unknown')}</code>\n"
            caption += f"• Channels: <code>{audio.get('channels', 'Unknown')}</code>\n"
            caption += f"• Bit Rate: <code>{audio.get('bit_rate', 'Unknown')}</code>\n"
            caption += f"• Language: <code>{audio.get('language', 'Unknown')}</code>\n\n"
    
    # Image info (for photos)
    if metadata.get("image"):
        caption += "🖼 <b>Image Information:</b>\n"
        caption += f"• Resolution: <code>{metadata['image'].get('width')} × {metadata['image'].get('height')}</code>\n"
        caption += f"• Color Space: <code>{metadata['image'].get('color_space', 'Unknown')}</code>\n"
        caption += f"• Compression: <code>{metadata['image'].get('compression', 'Unknown')}</code>\n\n"
    
    # Subtitles info
    if metadata.get("text"):
        caption += "📝 <b>Subtitle Track(s):</b>\n"
        for i, text in enumerate(metadata["text"], 1):
            caption += f"<b>Track {i}:</b>\n"
            caption += f"• Format: <code>{text.get('format', 'Unknown')}</code>\n"
            caption += f"• Language: <code>{text.get('language', 'Unknown')}</code>\n"
            caption += f"• Type: <code>{text.get('subtitle_type', 'Unknown')}</code>\n\n"
    
    return caption

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    bot_id = bot.me.id
    media = getattr(message, message.media.value, None)
    
    try:
        # Save file to database
        media.file_type = message.media.value
        media.caption = message.caption
        success_sts = await save_file(media)
        
        if success_sts == 'suc' and await db.get_send_movie_update_status(bot_id):
            file_id, file_ref = unpack_new_file_id(media.file_id)
            
            # Check for adult content
            is_adult = is_adult_content(media.file_name, message.caption)
            
            # Download the file temporarily to extract metadata
            temp_dir = "temp_files"
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, media.file_name or f"file_{file_id}")
            
            try:
                await message.download(file_name=temp_path)
                
                # Extract metadata
                metadata = extract_metadata(temp_path)
                file_name = media.file_name or metadata["general"].get("file_name", "Unknown")
                
                # Generate caption with adult tag if needed
                caption = generate_caption(file_name, metadata, is_adult)
                
                # Send update to channel
                await send_file_update(bot, file_name, caption, file_id, is_adult)
                
            except Exception as e:
                await bot.send_message(LOG_CHANNEL, f"Metadata extraction failed for {file_id}. Error: {str(e)}")
                # Fallback to simple message if metadata extraction fails
                simple_caption = f"🔞 <b>[ADULT CONTENT]</b> 🔞\n\n" if is_adult else ""
                simple_caption += f"📁 <b>File Name:</b> <code>{media.file_name or 'Unknown'}</code>\n"
                simple_caption += f"📦 <b>Type:</b> <code>{message.media.value.upper()}</code>\n"
                simple_caption += f"📝 <b>Caption:</b> <code>{message.caption or 'None'}</code>"
                await send_file_update(bot, media.file_name or "Unknown", simple_caption, file_id, is_adult)
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
    except Exception as e:
        await bot.send_message(LOG_CHANNEL, f"Error processing media: {str(e)}")

async def send_file_update(bot, file_name, caption, file_id, is_adult=False):
    """Send file update to channel with download buttons"""
    try:
        if file_name in processed_files:
            return
        processed_files.add(file_name)
        
        # Create buttons
        btn = [
            [InlineKeyboardButton('📂 ɢᴇᴛ ғɪʟᴇ 📂', url=f'https://telegram.me/{temp.U_NAME}?start={file_id}')],
            [InlineKeyboardButton('♻️ ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ ♻️', url='https://t.me/spideyofficial_777/12')]
        ]
        reply_markup = InlineKeyboardMarkup(btn)
        
        # Get update channel
        movie_update_channel = await db.movies_update_channel_id() or MOVIE_UPDATE_CHANNEL
        
        # Use different placeholder for adult content
        if is_adult:
            placeholder_image = "https://telegra.ph/file/2c3e5c4d5e6f7a8b9c0d1.jpg"  # NSFW warning image
        else:
            placeholder_image = "https://telegra.ph/file/88d845b4f8a024a71465d.jpg"  # Regular placeholder
        
        await bot.send_photo(
            chat_id=movie_update_channel,
            photo=placeholder_image,
            caption=caption,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        await bot.send_message(LOG_CHANNEL, f"Failed to send file update: {str(e)}")