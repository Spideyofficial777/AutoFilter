import base64
import mimetypes
import os

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction

from lexica import AsyncClient, languageModels, Messages


def get_prompt(message: Message):
    prompt = message.text.split(' ', 1)
    if len(prompt) < 2:
        return None
    return prompt[1]


def extract_content(response) -> str:
    if isinstance(response, dict) and 'content' in response:
        content = response['content']
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            return '\n'.join(item['text'] for item in content if isinstance(item, dict) and 'text' in item)
        elif isinstance(content, dict):
            if 'parts' in content and isinstance(content['parts'], list):
                return '\n'.join(part['text'] for part in content['parts'] if 'text' in part)
            return content.get('text', '')
    return "No content available."


def format_response(model_name: str, response_content: str) -> str:
    return f"**Model:** {model_name}\n\n**Response:**\n{response_content}"


async def handle_chat_model(message: Message, model_name: str, model):
    prompt = get_prompt(message)
    if not prompt:
        await message.reply_text("Please provide a prompt after the command.")
        return
    await message._client.send_chat_action(message.chat.id, ChatAction.TYPING)
    lexica_client = AsyncClient()
    try:
        messages = [Messages(content=prompt, role="user")]
        response = await lexica_client.ChatCompletion(messages, model)
        content = extract_content(response)
        await message.reply_text(format_response(model_name, content) if content else "No content received from the API.")
    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")
    finally:
        await lexica_client.close()


@Client.on_message(filters.command("bard"))
async def bard_handler(client: Client, message: Message):
    await handle_chat_model(message, "Bard", languageModels.bard)


@Client.on_message(filters.command("gemini"))
async def gemini_handler(client: Client, message: Message):
    await handle_chat_model(message, "Gemini", languageModels.gemini)


@Client.on_message(filters.command("gpt"))
async def gpt_handler(client: Client, message: Message):
    await handle_chat_model(message, "GPT", languageModels.gpt)


@Client.on_message(filters.command("llama"))
async def llama_handler(client: Client, message: Message):
    await handle_chat_model(message, "LLaMA", languageModels.llama)


@Client.on_message(filters.command("mistral"))
async def mistral_handler(client: Client, message: Message):
    await handle_chat_model(message, "Mistral", languageModels.mistral)


@Client.on_message(filters.command("geminivision"))
async def geminivision_handler(client: Client, message: Message):
    if not (message.reply_to_message and message.reply_to_message.photo):
        await message.reply_text("Please reply to an image with the /geminivision command and a prompt.")
        return
    
    prompt = get_prompt(message)
    if not prompt:
        await message.reply_text("Please provide a prompt after the command.")
        return
    
    await client.send_chat_action(message.chat.id, ChatAction.TYPING)
    status_message = await message.reply_text("Processing your image, please wait...")
    file_path = await client.download_media(message.reply_to_message.photo.file_id)
    lexica_client = AsyncClient()
    try:
        with open(file_path, "rb") as image_file:
            data = base64.b64encode(image_file.read()).decode("utf-8")
            mime_type, _ = mimetypes.guess_type(file_path)
            image_info = [{"data": data, "mime_type": mime_type}]
        
        response = await lexica_client.ChatCompletion(prompt, languageModels.geminiVision, images=image_info)
        content = extract_content(response)
        await message.reply_text(format_response("Gemini Vision", content) if content else "No content received from the API.")
    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")
    finally:
        await lexica_client.close()
        os.remove(file_path)
        await status_message.delete()


@Client.on_message(filters.command("upscale"))
async def upscale_handler(client: Client, message: Message):
    if not (message.reply_to_message and message.reply_to_message.photo):
        await message.reply_text("Please reply to the image you want to upscale with the /upscale command.")
        return
    
    await client.send_chat_action(message.chat.id, ChatAction.TYPING)
    status_message = await message.reply_text("<b>Upscaling your image, please wait...</b>")
    file_path = await client.download_media(message.reply_to_message.photo.file_id)
    lexica_client = AsyncClient()
    try:
        with open(file_path, "rb") as f:
            image_bytes = f.read()
        
        upscaled_image_bytes = await lexica_client.upscale(image_bytes)
        upscaled_image_path = "upscaled.png"
        with open(upscaled_image_path, "wb") as f:
            f.write(upscaled_image_bytes)
        
        await client.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
        await message.reply_photo(upscaled_image_path)
    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")
    finally:
        await lexica_client.close()
        os.remove(file_path)
        if os.path.exists(upscaled_image_path):
            os.remove(upscaled_image_path)
        await status_message.delete()
