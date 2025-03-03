import os
import asyncio
from aiohttp import ClientSession
from re import search as re_search
from pyrogram import Client, filters
from pymediainfo import MediaInfo

# Optional imports with fallbacks
try:
    from bot import LOGGER  # For logging (optional)
    from bot.helper.ext_utils.telegraph_helper import telegraph  # For Telegraph (optional)
    TELEGRAPH_AVAILABLE = True
except ImportError:
    LOGGER = None
    TELEGRAPH_AVAILABLE = False

CMD_HANDLER = "/"  # Adjust this to your bot's command prefix (e.g., "." if needed)

async def gen_mediainfo(client, message, link=None, media=None):
    """Generate MediaInfo from a link or replied media."""
    await message.edit("Processing media info... 🚀")  # Initial feedback
    temp_file = None
    try:
        if link:
            filename = re_search(r".+/(.+)", link).group(1) if re_search(r".+/(.+)", link) else f"media_{message.id}"
            temp_file = f"downloads/{filename}"
            os.makedirs("downloads", exist_ok=True)
            headers = {"user-agent": "Mozilla/5.0 (Linux; Android 12) Chrome/107.0.0.0"}
            async with ClientSession() as session:
                async with session.get(link, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Download failed: HTTP {response.status}")
                    with open(temp_file, "wb") as f:
                        f.write(await response.read())
        elif media:
            temp_file = f"downloads/{media.file_name or f'media_{message.id}'}.tmp"
            os.makedirs("downloads", exist_ok=True)
            if media.file_size <= 50_000_000:  # 50MB threshold
                await message.reply_to_message.download(file_name=temp_file)
            else:
                with open(temp_file, "wb") as f:
                    async for chunk in client.stream_media(message.reply_to_message, limit=10):
                        f.write(chunk)
                        await asyncio.sleep(0)  # Ensure responsiveness

        if not temp_file or not os.path.exists(temp_file):
            raise Exception("File not found or failed to download")

        media_info = MediaInfo.parse(temp_file)
        if not media_info.tracks:
            raise Exception("No metadata found")

        # Output options
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
            LOGGER.error(error_msg)
        await message.edit(error_msg)  # Ensure error is visible
        return None
    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)

async def parseinfo(media_info, html=False):
    """Parse MediaInfo into formatted text or HTML."""
    section_dict = {"General": "🗒", "Video": "🎞", "Audio": "🔊", "Text": "🔠", "Menu": "🗃", "Image": "🖼"}
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
            
            if track.track_type == "General":
                output += (f"File Name: {track.file_name or 'N/A'}\n"
                          f"Format: {track.format or 'N/A'}\n"
                          f"File Size: {track.file_size or 'N/A'} bytes\n"
                          f"Duration: {track.duration or 'N/A'} ms\n")
            elif track.track_type == "Video":
                output += (f"Format: {track.format or 'N/A'}\n"
                          f"Width: {track.width or 'N/A'} px\n"
                          f"Height: {track.height or 'N/A'} px\n"
                          f"Frame Rate: {track.frame_rate or 'N/A'} fps\n")
            elif track.track_type == "Audio":
                output += (f"Format: {track.format or 'N/A'}\n"
                          f"Channels: {track.channel_s or 'N/A'}\n"
                          f"Sampling Rate: {track.sampling_rate or 'N/A'} Hz\n")
            elif track.track_type == "Text":
                output += (f"Format: {track.format or 'N/A'}\n"
                          f"Language: {track.language or 'N/A'}\n")
            elif track.track_type == "Menu":
                output += f"Details: {track.to_data() or 'N/A'}\n"
            elif track.track_type == "Image":
                output += (f"Format: {track.format or 'N/A'}\n"
                          f"Width: {track.width or 'N/A'} px\n"
                          f"Height: {track.height or 'N/A'} px\n")
            if html:
                output += "</pre>"
    
    return output

@Client.on_message(filters.command(["media_info", "mediainfo"], CMD_HANDLER))
async def media_info(client, message):
    """Handle /media_info or /mediainfo command."""
    await message.edit("Command received, checking input...")  # Debug step 1: Confirm trigger
    
    link = None
    media = None

    # Input detection
    if len(message.command) > 1:
        link = message.command[1]
        await message.edit(f"Detected link: {link}")  # Debug step 2: Confirm link
    elif message.reply_to_message:
        if message.reply_to_message.text:
            link = message.reply_to_message.text.strip()
            await message.edit(f"Detected replied link: {link}")  # Debug step 3: Confirm replied link
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
            await message.edit(f"Detected media: {media.file_name if media else 'None'}")  # Debug step 4: Confirm media
    
    if not link and not media:
        await message.edit("Usage: `/media_info <link>` or reply to a media file/link.\nOptions: `json`, `tele`")
        return

    result = await gen_mediainfo(client, message, link=link, media=media)
    if result:
        if "https://graph.org/" in result:
            await message.edit(f"**Media Info Generated** 📌\n\n➲ [View Details]({result})", disable_web_page_preview=False)
        else:
            await message.edit(result[:4096])  # Telegram char limit
    # No else needed; errors are handled in gen_mediainfo
