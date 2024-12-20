import json
from bs4 import BeautifulSoup
import requests
import discord
from discord import FFmpegPCMAudio
from discord.ext import commands
from discord.ext.commands import Context
import yt_dlp
import logging
import logging.handlers

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
logging.getLogger('discord.http').setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename='logs/discord.log',
    encoding='utf-8',
    mode='w',
    maxBytes=32 * 1024 * 1024,
    backupCount=5,
)
date_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', date_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)

intents = discord.Intents.default()

command_prefix = "!"
command_list = [
    "play",
    "stop",
    "volume",
    "help"
]

# { guild_id: {"link": "name"} }
playlist_dict: dict[int, dict[str, str]] = {
    
}

# guild_id: song_index
playlist_index: dict[int, int] = {
    
}

TOKEN = open("private/token.txt", "r").read()
intents.message_content = True
bot = commands.Bot(command_prefix=command_prefix, intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user} has logged in...")


@bot.event
async def on_message(message):
    if message.author == bot.user: return

    content = message.content
    correct_command_usage = True

    if content.startswith(command_prefix):
        command = content[1:].split()[0]
        arguments = content[len(command_prefix) + len(command):].strip()

        print(f"Command: {command}")
        print(f"Arguments: {arguments}")

        if command == "play":
            if not arguments:
                correct_command_usage = False
                await message.channel.send(f"**You must provide a link with the `play` command!**")
    
    # Don't process commands if they weren't used properly
    if correct_command_usage:
        await bot.process_commands(message)


# Commands 
# Plays a song, if there's one playing already, replace it.
@bot.command()
async def play(ctx: Context, link: str):
    # Join user's voice channel if they're in one
    if ctx.author.voice:
        # Join the voice channel if we're not in it already
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()

        await ctx.guild.change_voice_state(channel=ctx.voice_client.channel, self_deaf=True)

        song = link
        url = None

        print(f"link: {link}")

        # Fetch an item from the guild's playlist
        if link.isdigit():
            song = await get_song_name(ctx, link)

            print(f"song: {song}")

            if song == None:
                await ctx.send("**That is not a valid position in your playlist!**")
                return

            url = await get_audio_url(song)
        if url == None:
            await add_song_to_playlist(ctx, link)

        # Check if `get_audio_url` returned with an error
        if url == None:
            await ctx.send(f"**There was an error fetching the audio!**")
            return

        song_name = await get_song_name(ctx, link, True)
        print(f"song_name: {song_name}")
        print(f"link: {link}")
        print(f"song: {song}")

        ctx.voice_client.stop()
        ctx.voice_client.play(FFmpegPCMAudio(url, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", options="-vn"))

        await ctx.send(f"**Now playing:**\n## `**{song_name}**`")
        await remove_song_from_playlist(ctx, song)
    else:
        await ctx.send("**You must be in a voice channel to use that command!**")


# Skips the current song, plays the next in queue.
@bot.command()
async def skip(ctx: Context):
    if not ctx.voice_client:
        await ctx.send(f"**I'm not currently in a voice channel!")
        return

    await ctx.send("**Skipping current song...**")

    if ctx.guild.id in playlist_dict and len(playlist_dict[ctx.guild.id]) == 0:
        await ctx.send(f"**Playlist is empty, just stopping song instead...**")
        return
    await play(1)
    print(f"playlist dict: {playlist_dict[ctx.guild.id]}")


# Displays the guild's playlist
@bot.command()
async def playlist(ctx: Context):
    # Create an empty entry if one doesn't exist
    await init_playlist(ctx)
    
    # playlist: dict[str, str] = playlist_dict[ctx.guild.id]
    playlist: list[str] = []
    playlist_message = ""
    
    for song in playlist_dict[ctx.guild.id].values():
        playlist.append(song)

    if len(playlist) == 0:
        await ctx.send(f"**Your playlist is empty!**")
        return
    
    for item in playlist:
        idx = playlist.index(item)
        playlist_message += f"\n## **{idx + 1}.** **`{playlist[idx]}`**" #| ({audio_length})"
   
    await ctx.send(f"## **Playlist:** ##" + playlist_message)


@bot.command()
async def add(ctx: Context, link: str):
    await ctx.send(f"**Adding that song to your playlist...**")

    if await add_song_to_playlist(ctx, link) == -1:
        await ctx.send(f"**That song is already on your playlist!**")


@bot.command()
async def clear(ctx: Context):
    playlist_dict[ctx.guild.id].clear()
    await ctx.send(f"**Playlist has been cleared!**")


@bot.command()
async def stop(ctx: Context):
    # Disconnect if the bot is in a voice channel
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        return
    await ctx.send("I am not currently in a voice channel!")
        

# <section>
# Helper methods
# </section>
async def get_info_dict(link: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'extractflat': True,
        'quiet': True,
    }
    # If the audio doesn't exist it will return an error
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:    return ydl.extract_info(link, download=False)
        except: return None


# Attempts to find audio stream url
async def get_audio_url(link: str):
    info_dict = await get_info_dict(link)

    if info_dict == None:
        print(f"Couldn't retrieve info_dict...")
        return None
        
    # Remove this later...
    with open("info_dict_dump.json", "w") as f:
        json.dump(info_dict, f, indent=5)

    if 'entries' in info_dict:
        for entry in info_dict['entries']:
            if entry.get('acodec') not in ['none', None] and 'audio' in entry['format']:
                return entry['url']
    elif 'formats' in info_dict:
        for format in info_dict['formats']:
            if format.get('acodec') not in ['none', None] and 'audio' in format['format']:
                return format['url']
    print(f"There was no url information in the received info_dict...")
    return None


# Creates an empty playlist
async def init_playlist(ctx: Context):
    if ctx.guild.id not in playlist_dict:
        playlist_dict[ctx.guild.id] = {}
        return


# Adds a song to the guild playlist
async def add_song_to_playlist(ctx: Context, link: str):
    if ctx.guild.id not in playlist_dict:
        await init_playlist(ctx)
    
    # Add the song if it's not in the playlist.
    if link in playlist_dict[ctx.guild.id]:
        print(f"already there, {link} | {playlist_dict[ctx.guild.id]}")
        return -1
    
    info_dict = await get_info_dict(link)
    audio_name = await get_audio_name(info_dict)
    playlist_dict[ctx.guild.id][link] = audio_name


async def remove_song_from_playlist(ctx: Context, link: str):
    if ctx.guild.id not in playlist_dict:
        await init_playlist(ctx)
    
    if link.isdigit():
        link = await get_song_name(ctx, link)
    playlist_dict[ctx.guild.id].pop(link)
    print(f"Removed {link} from playlist!")


# If not `name` returns link of song
# If `name` returns name of song
async def get_song_name(ctx: Context, link: str, name: bool = False):
    if not link.isdigit():
        print(f"Link is not a digit!")
        return None
    
    idx = int(link)

    if idx < 1 or idx > len(playlist_dict[ctx.guild.id]):
        print(f"index {idx} is outside the bounds of the playlist.")
        return None

    items = list(playlist_dict[ctx.guild.id].keys())
    if name:
        items = list(playlist_dict[ctx.guild.id].values())
    return items[idx - 1]
    

async def get_audio_name(info_dict: dict):
    if 'title' in info_dict:
        return info_dict['title']
    return None


async def get_audio_length(link: str):
    pass


bot.run(token=TOKEN)