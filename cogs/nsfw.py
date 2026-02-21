"""Simple NSFW media command."""

import discord
from discord.ext import commands
from discord import app_commands

class NSFW(commands.Cog):
    """Sends a predefined NSFW media clip."""

    def __init__(self, client):
        self.client = client

    @app_commands.command(name="nsfw", description="Mhh.. what could it possibly be?")
    async def nsfw(self, interaction: discord.Interaction):
        await interaction.response.send_message("DAMN BROO!!", file=discord.File("./media/1030.mp4"))

async def setup(client):
    """Register the cog in the bot instance."""
    await client.add_cog(NSFW(client))
