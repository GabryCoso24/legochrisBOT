"""Utility command for returning a user's Discord ID."""

import discord
from discord.ext import commands
from discord import app_commands

class ID(commands.Cog):
    """Exposes the slash command that prints a member ID."""

    def __init__(self, client):
        self.client = client

    @app_commands.command(name="id", description="Get a user id")
    async def id(self, interaction: discord.Interaction, member: discord.Member):
        embed_id = discord.Embed(title="Here is the ID you asked for", description=f"```{member.id}```", color=discord.Color.purple())
        embed_id.set_author(name=interaction.user, icon_url=interaction.user.avatar)
        embed_id.set_footer(text="ID", icon_url=interaction.guild.icon)
        await interaction.response.send_message(embed=embed_id)

async def setup(client):
    """Register the cog in the bot instance."""
    await client.add_cog(ID(client))
