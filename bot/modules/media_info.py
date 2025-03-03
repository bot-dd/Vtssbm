import os
from aiohttp import ClientSession
from re import search as re_search
from pyrogram import Client, filters
from pymediainfo import MediaInfo

# Optional imports with fallbacks
try:
    from bot import LOGGER
    from bot.helper.ext_utils.telegraph_helper import telegraph
    TELEGRAPH_AVAILABLE = True
except ImportError:
    LOGGER = None
    TELEGRAPH_AVAILABLE = False

CMD_HANDLER = "/"  # Verify this matches your bot's prefix

@Client.on_message(filters.command(["media_info", "mediainfo"], prefixes=CMD_HANDLER))
async def media_info(client, message):
    """Handle /media_info or /mediainfo with verbose feedback."""
    # Step 1: Confirm command trigger
    await message.edit_text("Step 1: Command triggered successfully.")
    await asyncio.sleep(1)  # Brief delay for visibility

    # Step 2: Detect input
    link = None
    media = None
    if len(message.command) > 1:
        link = message.command[1]
        await message.edit_text(f"Step 2: Link detected - {link}")
    elif message.reply_to_message:
        if message.reply_to_message.text:
            link = message.reply_to_message.text.strip()
            await message.edit_text(f"Step 2: Replied link detected - {link}")
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
            await message.edit_text(f"Step 2: Media detected - {media.file_name if media else 'None'}")
    else:
        await message.edit_text("Step 2: No input detected. Usage: `/media_info <link>` or reply to media/link.")
        return

    # Step 3: Process media info
    await message.edit_text("Step 3: Processing media info...")
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
                        raise Exception(f"HTTP {response.status}")
                    with open(temp_file, "wb") as f:
                        f.write(await response.read())
        elif media:
            temp_file = f"downloads/{media.file_name or f'media_{message.id}'}.tmp"
            os.makedirs("downloads", exist_ok=True)
            await message.reply_to_message.download(file_name=temp_file)  # Simplified: no streaming for now

        if not temp_file or not os.path.exists(temp_file):
            raise Exception("File not downloaded")

        # Step 4: Parse metadata
        await message.edit_text("Step 4: Parsing metadata...")
        media_info = MediaInfo.parse(temp_file)
        if not media_info.tracks:
            raise Exception("No metadata found")

        # Step 5: Generate output
        await message.edit_text("Step 5: Generating output...")
        if "json" in message.text.lower():
            output = media_info.to_json()
        elif TELEGRAPH_AVAILABLE and "tele" in message.text.lower():
            output = parseinfo(media_info, html=True)
            link_id = (await telegraph.create_page(title=f"MediaInfo - {message.id}", content=output))["path"]
            output = f"https://graph.org/{link_id}"
        else:
            output = parseinfo(media_info, html=False)

        # Step 6: Deliver result
        if "https://graph.org/" in output:
            await message.edit_text(f"**Media Info** 📌\n\n➲ [View Details]({output})", disable_web_page_preview=False)
        else:
            await message.edit_text(output[:4096])
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        if LOGGER:
            LOGGER.info(error_msg)  # Use INFO to ensure it logs
        await message.edit_text(error_msg)
    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
            if LOGGER:
                LOGGER.info(f"Cleaned up: {temp_file}")

def parseinfo(media_info, html=False):
    """Parse MediaInfo into text or HTML."""
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
