import os
import asyncio
from aiohttp import ClientSession
from re import search as re_search
from pyrogram import Client, filters
from pymediainfo import MediaInfo

# Optional imports for enhanced features; gracefully skipped if unavailable
try:
    from bot import LOGGER  # For logging errors
    from bot.helper.ext_utils.telegraph_helper import telegraph  # For Telegraph output
    TELEGRAPH_AVAILABLE = True
except ImportError:
    LOGGER = None
    TELEGRAPH_AVAILABLE = False

CMD_HANDLER = "/"  # Adjust this to your bot's command prefix

async def gen_mediainfo(client, message, link=None, media=None):
    """Generate MediaInfo from a link or replied media with optimal speed."""
    await message.edit("Processing media info... 🚀")
    temp_file = None
    try:
        # Handle link input
        if link:
            filename = re_search(r".+/(.+)", link).group(1) if re_search(r".+/(.+)", link) else f"media_{message.id}"
            temp_file = f"downloads/{filename}"
            os.makedirs("downloads", exist_ok=True)  # Fast directory creation
            headers = {
                "user-agent": "Mozilla/5.0 (Linux; Android 12; 2201116PI) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36"
            }
            async with ClientSession() as session:
                async with session.get(link, headers=headers) as response:
                    if response.status == 200:
                        with open(temp_file, "wb") as f:  # Synchronous write for simplicity and speed
                            f.write(await response.read())  # Single read for faster downloads
                    else:
                        raise Exception(f"Failed to download: HTTP {response.status}")
        
        # Handle replied media
        elif media:
            temp_file = f"downloads/{media.file_name or f'media_{message.id}'}.tmp"
            os.makedirs("downloads", exist_ok=True)
            if media.file_size <= 50_000_000:  # 50MB threshold for direct download
                await message.reply_to_message.download(file_name=temp_file)
            else:  # Stream large files efficiently
                async with open(temp_file, "wb") as f:
                    async for chunk in client.stream_media(message.reply_to_message, limit=10):  # Increased limit for completeness
                        await f.write(chunk)
                        await asyncio.sleep(0)  # Yield control for responsiveness

        # Parse media info with pymediainfo
        if not temp_file or not os.path.exists(temp_file):
            raise Exception("No file to process")
        
        media_info = MediaInfo.parse(temp_file)
        if not media_info.tracks:
            raise Exception("No metadata found in file")

        # Output options: JSON, Telegraph, or plain text
        if "json" in message.text.lower():
            output = media_info.to_json()
        elif TELEGRAPH_AVAILABLE and "tele" in message.text.lower():
            formatted_output = await parseinfo(media_info, html=True)
            link_id = (await telegraph.create_page(title=f"MediaInfo - {message.id}", content=formatted_output))["path"]
            output = f"https://graph.org/{link_id}"
        else:
            output = await parseinfo(media_info, html=False)
        
        return output
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        if LOGGER:
            LOGGER.error(f"MediaInfo Failure: {error_msg}")
        await message.edit(error_msg)
        return None
    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)

async def parseinfo(media_info, html=False):
    """Parse MediaInfo into a detailed, formatted string (HTML or plain text)."""
    section_dict = {
        "General": "🗒",
        "Video": "🎞",
        "Audio": "🔊",
        "Text": "🔠",
        "Menu": "🗃",
        "Image": "🖼"
    }
    output = "<h4>📌 Media Info</h4><br><br>" if html else "**Media Info** 📌\n\n"
    
    for track in media_info.tracks:
        if track.track_type in section_dict:
            if html and track.track_type != "General":
                output += "</pre><br>"
            emoji = section_dict[track.track_type]
            section_name = "Subtitle" if track.track_type == "Text" else track.track_type
            output += f"<h4>{emoji} {section_name}</h4>" if html else f"{emoji} **{section_name}**\n"
            if html:
                output += "<br><pre>"
            
            # General track
            if track.track_type == "General":
                output += (f"File Name: {track.file_name or 'N/A'}\n"
                          f"Format: {track.format or 'N/A'}\n"
                          f"File Size: {track.file_size or 'N/A'} bytes\n"
                          f"Duration: {track.duration or 'N/A'} ms\n"
                          f"Overall Bit Rate: {track.overall_bit_rate or 'N/A'} bps\n")
            
            # Video track
            elif track.track_type == "Video":
                output += (f"Format: {track.format or 'N/A'}\n"
                          f"Codec: {track.codec_id or 'N/A'}\n"
                          f"Width: {track.width or 'N/A'} px\n"
                          f"Height: {track.height or 'N/A'} px\n"
                          f"Frame Rate: {track.frame_rate or 'N/A'} fps\n"
                          f"Bit Rate: {track.bit_rate or 'N/A'} bps\n")
            
            # Audio track
            elif track.track_type == "Audio":
                output += (f"Format: {track.format or 'N/A'}\n"
                          f"Codec: {track.codec_id or 'N/A'}\n"
                          f"Channels: {track.channel_s or 'N/A'}\n"
                          f"Sampling Rate: {track.sampling_rate or 'N/A'} Hz\n"
                          f"Bit Rate: {track.bit_rate or 'N/A'} bps\n")
            
            # Text (Subtitle) track
            elif track.track_type == "Text":
                output += (f"Format: {track.format or 'N/A'}\n"
                          f"Language: {track.language or 'N/A'}\n"
                          f"Title: {track.title or 'N/A'}\n")
            
            # Menu track
            elif track.track_type == "Menu":
                output += f"Details: {track.to_data() or 'N/A'}\n"
            
            # Image track (for photos)
            elif track.track_type == "Image":
                output += (f"Format: {track.format or 'N/A'}\n"
                          f"Width: {track.width or 'N/A'} px\n"
                          f"Height: {track.height or 'N/A'} px\n")
            
            if html:
                output += "</pre>"

    return output

@Client.on_message(filters.command("media_info", CMD_HANDLER))
async def media_info(client, message):
    """Handle /media_info command with maximum flexibility and speed."""
    link = None
    media = None

    # Detect input: command link, replied link, or replied media
    if len(message.command) > 1:
        link = message.command[1]
    elif message.reply_to_message:
        if message.reply_to_message.text:
            link = message.reply_to_message.text.strip()
        elif message.reply_to_message.media:
            media = next(
                (
                    i for i in [
                        message.reply_to_message.document,
                        message.reply_to_message.video,
                        message.reply_to_message.audio,
                        message.reply_to_message.photo,
                        message.reply_to_message.voice,
                        message.reply_to_message.animation,
                        message.reply_to_message.video_note,
                    ] if i is not None
                ),
                None,
            )

    if not link and not media:
        return await message.edit("Usage: `/media_info <link>` or reply to a media file/link with `/media_info`.\nAdd `json` or `tele` for alternative outputs.")

    result = await gen_mediainfo(client, message, link=link, media=media)
    if result:
        if "https://graph.org/" in result:  # Telegraph output
            await message.edit(f"**Media Info Generated** 📌\n\n➲ [View Details]({result})", disable_web_page_preview=False)
        else:  # Plain text or JSON
            await message.edit(result[:4096])  # Respect Telegram's 4096-char limit
    # Error case is handled in gen_mediainfo
