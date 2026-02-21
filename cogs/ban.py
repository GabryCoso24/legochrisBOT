"""Moderation commands for banning and unbanning members."""

import discord
from discord.ext import commands
from discord import app_commands

class Ban(commands.Cog):
    """Provides slash commands for ban and unban operations."""

    def __init__(self, client):
        self.client = client

    @app_commands.command(name='ban', description='Banna un membro del server')
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Nessun motivo fornito"):
        guild = interaction.guild
        try:
            await guild.ban(member, reason=reason)
            embed_message = discord.Embed(
                title="User Banned",
                description=f"{member.mention} è stato bannato da {interaction.user.mention}",
                color=discord.Color.orange()
            )
            embed_message.set_author(name=interaction.user.name, icon_url=interaction.user.avatar)
            embed_message.set_footer(text="Ban", icon_url=self.client.user.avatar)
            embed_message.add_field(name="Reason", value=reason)
            await interaction.response.send_message(embed=embed_message)
        except Exception as e:
            embed_message = discord.Embed(
                title="Ban Failed",
                description=f"An error occurred while banning {member.mention}: {str(e)})",
                color=discord.Color.red()
            )
            embed_message.set_author(name=interaction.user.name, icon_url=interaction.user.avatar)
            embed_message.set_footer(text="Ban", icon_url=self.client.user.avatar)
            embed_message.add_field(name="Reason", value=reason)
            await interaction.response.send_message(embed=embed_message)

    @app_commands.command(name='unban', description="Sbanna un utente bannato dal server (fornendo l'ID del'utente)")
    @app_commands.describe(member = "Inserisci l'ID del utente per sbannarlo")
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, member: str, reason: str = "Nessun motivo fornito"):
        user = discord.Object(id=member)
        try:
            await interaction.guild.unban(user)
            embed_message = discord.Embed(
                title="User Unbanned",
                description=f"<@{member}> è stato sbannato da <@{interaction.user.id}>",
                color=discord.Color.orange()
            )
            embed_message.set_author(name=interaction.user.name, icon_url=interaction.user.avatar)
            embed_message.set_footer(text="Unban", icon_url=self.client.user.avatar)
            embed_message.add_field(name="Reason", value=reason)
            await interaction.response.send_message(embed=embed_message)
        except Exception as e:
            embed_message = discord.Embed(
                title="Unban Failed",
                description=f"An error occurred while unbanning <@{member}>: {str(e)}",
                color=discord.Color.orange()
            )
            embed_message.set_author(name=interaction.user.name, icon_url=interaction.user.avatar)
            embed_message.set_footer(text="Unban", icon_url=self.client.user.avatar)
            embed_message.add_field(name="Reason", value=reason)
            await interaction.response.send_message(embed=embed_message)

async def setup(client):
    """Register the cog in the bot instance."""
    await client.add_cog(Ban(client))
