import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# Environment Variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL"))
PORT = int(os.environ.get("PORT", 8080))
URL = os.environ.get("URL")

app = Client("StreamBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
routes = web.RouteTableDef()

@routes.get("/")
async def root_route_handler(request):
    return web.json_response({"status": "Bot is Running Successfully!", "version": "2.0-Pro"})

# High-Speed Range Header & Streaming Handler (Seekable Support)
@routes.get("/stream/{msg_id}")
@routes.get("/download/{msg_id}")
async def media_stream_handler(request):
    try:
        msg_id = int(request.match_info["msg_id"])
        message = await app.get_messages(BIN_CHANNEL, msg_id)
        
        if not message or not (message.document or message.video or message.audio):
            return web.Response(status=404, text="File Not Found")
            
        media = message.document or message.video or message.audio
        file_size = media.file_size
        mime_type = media.mime_type or "application/octet-stream"
        file_name = media.file_name or "file"
        
        # Determine if request is direct download or inline stream
        is_download = "/download/" in request.path
        disposition = "attachment" if is_download else "inline"

        range_header = request.headers.get("Range")
        
        if range_header:
            from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
            from_bytes = int(from_bytes)
            until_bytes = int(until_bytes) if until_bytes else file_size - 1
        else:
            from_bytes = 0
            until_bytes = file_size - 1

        length = until_bytes - from_bytes + 1

        headers = {
            "Content-Type": mime_type,
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        }

        response = web.StreamResponse(status=206 if range_header else 200, headers=headers)
        await response.prepare(request)

        # Fast chunked streaming loop (64KB chunks)
        async for chunk in app.stream_media(message, offset=from_bytes, limit=length):
            await response.write(chunk)

        return response
    except Exception as e:
        return web.Response(status=500, text=str(e))

# Welcome Message for /start
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    welcome_text = (
        f"<b>👋 হ্যালো {message.from_user.mention},</b>\n\n"
        f"আমি একটি <b>High-Speed Telegram File Streaming & Download Bot</b>।\n\n"
        f"<b>🚀 যেভাবে কাজ করবেন:</b>\n"
        f"যেকোনো ভিডিও, অডিও বা ফাইল আমাকে পাঠান। আমি আপনাকে সাথে সাথে "
        f"<b>Online Stream Link</b> এবং <b>Direct Download Link</b> তৈরি করে দেব!"
    )
    await message.reply_text(welcome_text, quote=True)

# Media Handling Logic
@app.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_media(client, message):
    # Copy file to private storage channel
    log_msg = await message.copy(chat_id=BIN_CHANNEL)
    
    base_url = URL.rstrip("/")
    stream_link = f"{base_url}/stream/{log_msg.id}"
    download_link = f"{base_url}/download/{log_msg.id}"
    
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶️ Fast Stream", url=stream_link),
            InlineKeyboardButton("📥 Direct Download", url=download_link)
        ]
    ])
    
    media = message.document or message.video or message.audio
    file_name = media.file_name or "Media File"
    
    text = (
        f"<b>📁 File Name:</b> <code>{file_name}</code>\n\n"
        f"🔗 <b>Stream Link:</b> {stream_link}\n\n"
        f"📥 <b>Download Link:</b> {download_link}"
    )
    
    await message.reply_text(
        text=text,
        reply_markup=reply_markup,
        quote=True
    )

async def start_services():
    await app.start()
    server = web.Application()
    server.add_routes(routes)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())
