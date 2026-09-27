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
    return web.json_response({"status": "Bot is Running Successfully!"})

@routes.get("/stream/{msg_id}")
async def stream_handler(request):
    try:
        msg_id = int(request.match_info["msg_id"])
        message = await app.get_messages(BIN_CHANNEL, msg_id)
        
        if not message or not (message.document or message.video or message.audio):
            return web.Response(status=404, text="File Not Found")
            
        media = message.document or message.video or message.audio
        file_size = media.file_size
        
        response = web.StreamResponse()
        response.content_type = media.mime_type or "application/octet-stream"
        response.headers["Content-Disposition"] = f'inline; filename="{media.file_name or "file"}"'
        response.headers["Content-Length"] = str(file_size)
        
        await response.prepare(request)
        
        async for chunk in app.stream_media(message):
            await response.write(chunk)
            
        return response
    except Exception as e:
        return web.Response(status=500, text=str(e))

@app.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_media(client, message):
    # Forward message to Private Channel
    log_msg = await message.copy(chat_id=BIN_CHANNEL)
    
    # Stream & Download Link
    base_url = URL.rstrip("/")
    stream_link = f"{base_url}/stream/{log_msg.id}"
    
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Fast Stream / Download 🚀", url=stream_link)]
    ])
    
    await message.reply_text(
        text=f"<b>Your File is Ready!</b>\n\n<b>Link:</b> {stream_link}",
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
