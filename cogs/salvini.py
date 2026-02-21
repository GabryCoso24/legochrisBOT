"""Small media command that posts a random Salvini image."""

import discord
from discord.ext import commands
import random


salvini = [discord.File("./media/salvini1.png") , discord.File("./media/salvini.png")]

client = commands.Bot(command_prefix= '!', intents=discord.Intents.all())

class salvinis(commands.Cog):
    """Legacy random-image command group."""

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("salvini funziona")
    

    @commands.command()
    async def salvini(self, ctx):
        await ctx.send(file = random.choice(salvini))


async def setup(client):
    """Register the cog in the bot instance."""
    await client.add_cog(salvinis(client))