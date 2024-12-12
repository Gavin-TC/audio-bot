import discord

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

token = open("token.txt", "r").read()

@client.event
async def on_ready():
    print(f"{client.user} has logged in...")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("$hello"):
        await message.channel.send("Hello!")

client.run(token=token)