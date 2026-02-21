"""Main entrypoint for the Discord bot runtime and cog loading."""

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio

# Load environment variables from .env (TOKEN, API keys, etc.)
load_dotenv()


TOKEN = os.getenv('TOKEN')
# Enable the intents required by the configured cogs.
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.guilds = True

client = commands.Bot(command_prefix='!', intents=intents)

@client.event
async def on_ready():
    """Run startup sync tasks and publish bot presence once connected."""
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="🧱 | I Mattoncini di LegoChris"))
    await client.tree.sync()
    print('---------------------------')
    print(f'Logged in as {client.user}')
    print('---------------------------')
    await client.tree.sync(guild=discord.Object(id=1054798470617255966))

async def load():
    """Dynamically load every cog module found in the cogs folder."""
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            try:
                await client.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ {filename[:-3]} is loaded")
            except Exception as e:
                print(f"❌ Failed to load {filename[:-3]}: {str(e)}")

async def main():
    """Open bot session, load cogs and start the Discord gateway connection."""
    async with client:
        await load()
        await client.start(TOKEN)

asyncio.run(main())