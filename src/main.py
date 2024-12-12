import json
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
                await message.channel.send(f"You must provide a link with the `play` command!")

    # Don't process commands if they weren't used properly
    if correct_command_usage:
        await bot.process_commands(message)


# Commands 
@bot.command()
async def play(ctx: Context, link: str):
    # Join user's voice channel if they're in one
    if ctx.author.voice:
        # Join the voice channel if we're not in it already
        if not ctx.voice_client: await ctx.author.voice.channel.connect()

        # Stop playing audio if it's already playing
        if ctx.voice_client.is_playing():
            await ctx.send(f"**Currently playing song!**")
        else:
            url = await get_audio_url(link)
            if url == None:
                await ctx.send(f"There was an error fetching the audio!")
                return
            
            print(f"url: {url}")
            
            ctx.voice_client.play(FFmpegPCMAudio(url))
            await ctx.send(f"***Now playing:***\n{link}")
        
    else:
        await ctx.send("You must be in a voice channel to use that command!")


async def get_audio_url(link: str):
    ydl_opts = {
        'format': 'bestaudio',
        'extractaudio': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(link, download=False)
        
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


@bot.command()


@bot.command()
async def stop(ctx: Context):
    # Disconnect if the bot is in a voice channel
    if ctx.voice_client: await ctx.voice_client.disconnect()
    else:                await ctx.send("I am not currently in a voice channel!")
        

bot.run(token=TOKEN)