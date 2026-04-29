import os
import asyncio
import json
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")

app = Client("voicebot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

playlist = []
current_index = 0
is_playing = False
stream_process = None

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
         InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("🎙 Live Control", callback_data="live_control")],
        [InlineKeyboardButton("🔄 Restart", callback_data="restart")]
    ])

def live_control_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Play", callback_data="play"),
         InlineKeyboardButton("⏹ Stop", callback_data="stop")],
        [InlineKeyboardButton("⏭ Next", callback_data="next")],
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
            [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
        ])
    )

@app.on_callback_query()
async def callbacks(client, query):
    global current_index, is_playing, playlist
    data = query.data
    if data == "back_main":
        await query.message.edit_text(
            "🎙 **VOICE STREAM BOT**\n\nKya karna chahte hain?",
            reply_markup=main_menu()
        )
    elif data == "playlist":
        await query.message.edit_text(
            "🎵 **PLAYLIST**\n\nAudio manage karein:",
            reply_markup=playlist_menu()
        )
    elif data == "add_audio":
        await query.message.edit_text(
            "🎵 **AUDIO ADD KAREIN**\n\nBas MP3 file bhejein!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="playlist")]
            ])
        )
    elif data == "show_list":
        load_playlist()
        if not playlist:
            text = "📋 Playlist khaali hai!"
        else:
            text = "📋 **PLAYLIST:**\n\n"
            for i, audio in enumerate(playlist):
                marker = "▶️" if i == current_index and is_playing else f"{i+1}."
                text += f"{marker} {audio['name']}\n"
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="playlist")]
            ])
        )
    elif data == "clear_all":
        playlist = []
        save_playlist()
        await query.message.edit_text("🗑 Playlist clear ho gayi!", reply_markup=playlist_menu())
    elif data == "live_control":
        status = "🟢 Playing" if is_playing else "🔴 Stopped"
        await query.message.edit_text(
            f"🎙 **LIVE CONTROL**\n\nStatus: {status}\nPlaylist: {len(playlist)} audio",
            reply_markup=live_control_menu()
        )
    elif data == "play":
        load_playlist()
        if not playlist:
            await query.answer("❌ Playlist khaali hai!", show_alert=True)
            return
        await query.answer("▶️ Starting...")
        await query.message.edit_text("▶️ Stream shuru ho raha hai...", reply_markup=live_control_menu())
        is_playing = True
    elif data == "stop":
        is_playing = False
        await query.message.edit_text("⏹ Stream band ho gaya!", reply_markup=main_menu())
    elif data == "next":
        current_index = (current_index + 1) % len(playlist) if playlist else 0
        await query.answer(f"⏭ Next: {playlist[current_index]['name']}" if playlist else "Playlist khaali!")
    elif data == "status":
        status = "🟢 Live Chal Raha Hai" if is_playing else "🔴 Band Hai"
        current = playlist[current_index]['name'] if playlist and is_playing else "Kuch nahi"
        await query.message.edit_text(
            f"📊 **STATUS**\n\n🎙 Stream: {status}\n🎵 Current: {current}\n📋 Playlist: {len(playlist)} audio",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
            ])
        )
    elif data == "restart":
        await query.answer("🔄 Restarting...")
        is_playing = False
        await asyncio.sleep(1)
        is_playing = True
        await query.message.edit_text("🔄 Restarted!", reply_markup=main_menu())

load_playlist()
app.run()
