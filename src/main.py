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

# guild_id: ["link"]
playlist_dict: dict[int, list[str]] = {
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
@bot.command()
async def play(ctx: Context, link: str):
    # Join user's voice channel if they're in one
    if ctx.author.voice:
        # Join the voice channel if we're not in it already
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
        await ctx.guild.change_voice_state(channel=ctx.voice_client.channel, self_deaf=True)

        url = await get_audio_url(link)
        if url == None:
            await ctx.send(f"**There was an error fetching the audio!**")
            return

        if ctx.voice_client.is_playing():
            await add(ctx, link) # Add the song to the guild's playlist
        else:
            ctx.voice_client.play(FFmpegPCMAudio(url))
            await ctx.send(f"**Now playing:**\n{link}")
    else:
        await ctx.send("**You must be in a voice channel to use that command!**")



# Skips the current song, plays the next in queue.
@bot.command()
async def skip(ctx: Context):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()

    await ctx.send("**Skipping current song...**")
    # If there's a song in the playlist, play it
    # If not, then basically act as stop()
    if len(playlist_dict[ctx.guild.id]) == 0:
        await play(ctx, playlist_dict[ctx.guild.id][0])
        playlist_dict[ctx.guild.id].pop(0)

    print(f"playlist dict: {playlist_dict[ctx.guild.id]}")


# Displays the guild's playlist
@bot.command()
async def playlist(ctx: Context):
    # Create an empty entry if one doesn't exist
    if ctx.guild.id not in playlist_dict:
        playlist_dict[ctx.guild.id] = []
    
    playlist: list[str] = playlist_dict[ctx.guild.id]
    playlist_message = ""

    if len(playlist) == 0:
        await ctx.send(f"**Your playlist is empty!**")
        return
    
    for item in playlist:
        audio_name = await get_audio_name(item)

        if audio_name != None:
            print(f"playlist item name: {audio_name}")
        else:
            print(f"playlist item: {item}")

        playlist_message += f"\n## **{playlist.index(item) + 1}.** **`{audio_name}`**" #| ({audio_length})"
    
    await ctx.send(f"**Playlist:**" + playlist_message)


@bot.command()
async def add(ctx: Context, link: str):
    await ctx.send(f"**Adding that song to your playlist...**")
    await add_song_to_playlist(ctx, link)


@bot.command()
async def clear(ctx: Context):
    playlist_dict[ctx.guild.id] = []
    await ctx.send(f"**Playlist has been cleared!**")


@bot.command()
async def stop(ctx: Context):
    # Disconnect if the bot is in a voice channel
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        return
    await ctx.send("I am not currently in a voice channel!")
        

# Helper methods

async def get_info_dict(link: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'extractflat': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # If the audio doesn't exist it will return an error
        try:
            return ydl.extract_info(link, download=False)
        except:
            return None

# Attempts to find audio stream url
async def get_audio_url(link: str):
    info_dict = await get_info_dict(link)

    if info_dict == None:
        return None
        
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
    return None


# Adds a song to the guild playlist
async def add_song_to_playlist(ctx: Context, link: str):
    if ctx.guild.id not in playlist_dict:
        playlist_dict[ctx.guild.id] = []
    playlist_dict[ctx.guild.id].append(link)


async def get_audio_name(link: str):
    info_dict = await get_info_dict(link)

    with open("info_dict_dump2.json", "w") as f:
        json.dump(info_dict, f, indent=5)

    if 'title' in info_dict:
        return info_dict['title']
    return None


async def get_audio_length(link: str):
    pass


bot.run(token=TOKEN)