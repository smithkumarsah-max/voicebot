import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
import json

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))

app = Client("voicebot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
call_py = PyTgCalls(app)

playlist = []
current_index = 0
is_playing = False

def save_playlist():
    with open("playlist.json", "w") as f:
        json.dump(playlist, f)

def load_playlist():
    global playlist
    try:
        with open("playlist.json", "r") as f:
            playlist = json.load(f)
    except:
        playlist = []

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎵 Playlist", callback_data="playlist"),
         InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("🎙 Live Control", callback_data="live_control"),
         InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("🔄 Restart", callback_data="restart")]
    ])

def live_control_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Play", callback_data="play"),
         InlineKeyboardButton("⏹ Stop", callback_data="stop")],
        [InlineKeyboardButton("⏭ Next", callback_data="next"),
         InlineKeyboardButton("🔁 Replay", callback_data="replay")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ])

def playlist_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Audio Add", callback_data="add_audio"),
         InlineKeyboardButton("🗑 Clear All", callback_data="clear_all")],
        [InlineKeyboardButton("📋 List Dekho", callback_data="show_list")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ])

@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start(client, message: Message):
    load_playlist()
    await message.reply(
        "🎙 **VOICE STREAM BOT**\n\n"
        f"👤 Account: {message.from_user.first_name}\n"
        "🟢 Status: Active\n\nKya karna chahte hain?",
        reply_markup=main_menu()
    )

@app.on_message(filters.command("start"))
async def unauthorized(client, message: Message):
    await message.reply("🔒 Unauthorized.")

@app.on_message((filters.audio | filters.voice | filters.document) & filters.user(OWNER_ID))
async def receive_audio(client, message: Message):
    global playlist
    msg = await message.reply("⏳ Audio download ho raha hai...")
    file_name = f"audio_{len(playlist)+1}.mp3"
    await message.download(file_name=file_name)
    if message.audio:
        audio_name = message.audio.file_name or f"Audio {len(playlist)+1}"
    elif message.document:
        audio_name = message.document.file_name or f"Audio {len(playlist)+1}"
    else:
        audio_name = f"Audio {len(playlist)+1}"
    playlist.append({"name": audio_name, "file": file_name})
    save_playlist()
    await msg.edit(
        f"✅ **Added:**\n🎵 {audio_name}\n\nPlaylist mein total: {len(playlist)} audio",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Abhi Play Karein", callback_data="play")],
            [InlineKeyboardButton("➕ Aur Add Karein", callback_data="add_audio")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
        ])
    )

@app.on_callback_query()
async def callbacks(client, query):
    global current_index, is_playing, playlist
    data = query.data
    if data == "back_main":
        await query.message.edit_text("🎙 **VOICE STREAM BOT**\n\nKya karna chahte hain?", reply_markup=main_menu())
    elif data == "playlist":
        await query.message.edit_text("🎵 **PLAYLIST**\n\nAudio manage karein:", reply_markup=playlist_menu())
    elif data == "add_audio":
        await query.message.edit_text("🎵 **AUDIO ADD KAREIN**\n\nBas MP3 file bhejein!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="playlist")]]))
    elif data == "show_list":
        load_playlist()
        if not playlist:
            text = "📋 Playlist khaali hai!"
        else:
            text = "📋 **PLAYLIST:**\n\n"
            for i, audio in enumerate(playlist):
                marker = "▶️" if i == current_index and is_playing else f"{i+1}."
                text += f"{marker} {audio['name']}\n"
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="playlist")]]))
    elif data == "clear_all":
        playlist = []
        save_playlist()
        await query.message.edit_text("🗑 Playlist clear ho gayi!", reply_markup=playlist_menu())
    elif data == "live_control":
        status = "🟢 Playing" if is_playing else "🔴 Stopped"
        await query.message.edit_text(f"🎙 **LIVE CONTROL**\n\nStatus: {status}\nPlaylist: {len(playlist)} audio", reply_markup=live_control_menu())
    elif data == "play":
        load_playlist()
        if not playlist:
            await query.answer("❌ Playlist khaali hai!", show_alert=True)
            return
        await query.answer("▶️ Starting...")
        await start_stream(query.message)
    elif data == "stop":
        await stop_stream(query.message)
    elif data == "next":
        await next_song(query.message)
    elif data == "replay":
        await start_stream(query.message)
    elif data == "status":
        status = "🟢 Live Chal Raha Hai" if is_playing else "🔴 Band Hai"
        current = playlist[current_index]['name'] if playlist and is_playing else "Kuch nahi"
        await query.message.edit_text(f"📊 **STATUS**\n\n🎙 Stream: {status}\n🎵 Current: {current}\n📋 Playlist: {len(playlist)} audio", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_main")]]))
    elif data == "restart":
        await query.answer("🔄 Restarting...")
        await stop_stream(query.message)
        await asyncio.sleep(2)
        await start_stream(query.message)

async def start_stream(message):
    global is_playing, current_index
    if not playlist:
        await message.reply("❌ Playlist khaali hai!")
        return
    try:
        audio_file = playlist[current_index]['file']
        audio_name = playlist[current_index]['name']
        await call_py.join_group_call(CHANNEL_ID, AudioPiped(audio_file))
        is_playing = True
        await message.reply(f"▶️ **Playing:**\n🎵 {audio_name}\n\n📋 {current_index+1}/{len(playlist)}", reply_markup=live_control_menu())
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

async def stop_stream(message):
    global is_playing
    try:
        await call_py.leave_group_call(CHANNEL_ID)
        is_playing = False
        await message.reply("⏹ Stream band ho gaya!", reply_markup=main_menu())
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

async def next_song(message):
    global current_index
    if not playlist:
        await message.reply("❌ Playlist khaali hai!")
        return
    current_index = (current_index + 1) % len(playlist)
    await start_stream(message)

@call_py.on_stream_end()
async def stream_end(_, update):
    global current_index
    current_index = (current_index + 1) % len(playlist)
    if playlist:
        await call_py.join_group_call(CHANNEL_ID, AudioPiped(playlist[current_index]['file']))

load_playlist()
call_py.start()
app.run()
