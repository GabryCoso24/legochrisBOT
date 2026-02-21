"""Persistent reaction-role management with add/remove listeners."""


import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class ReactionRoles(commands.Cog):
    """Maps message reactions to role assignment and removal."""

    @app_commands.command(name="removereactionrole", description="Rimuovi un reaction role da un messaggio")
    @app_commands.describe(message_id="ID del messaggio", emoji="Emoji della reazione da rimuovere")
    async def removereactionrole(self, interaction: discord.Interaction, message_id: str, emoji: str):
        try:
            message_id_int = int(message_id)
        except ValueError:
            await interaction.response.send_message("❌ ID messaggio non valido.", ephemeral=True)
            return
        if message_id_int not in self.message_id_to_roles or emoji not in self.message_id_to_roles[message_id_int]:
            await interaction.response.send_message("❌ Reaction role non trovato per questo messaggio/emoji.", ephemeral=True)
            return
        del self.message_id_to_roles[message_id_int][emoji]
        if not self.message_id_to_roles[message_id_int]:
            del self.message_id_to_roles[message_id_int]
        self.save_reaction_roles()

        # Prova a rimuovere la reazione dal messaggio target
        try:
            channel = interaction.channel
            message = await channel.fetch_message(message_id_int)
            await message.clear_reaction(emoji)
            msg = f"✅ Reaction role rimosso: {emoji} dal messaggio {message_id} (reazione rimossa dal messaggio)"
        except Exception as e:
            msg = f"✅ Reaction role rimosso: {emoji} dal messaggio {message_id}\n⚠️ Non sono riuscito a rimuovere la reazione in automatico: {e}"
        await interaction.response.send_message(msg, ephemeral=True)
    def __init__(self, bot):
        self.bot = bot
        self.data_path = os.path.join("data", "reactionroles", "reactionroles.json")
        self.message_id_to_roles = self.load_reaction_roles()

    def load_reaction_roles(self):
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {int(mid): {e: rid for e, rid in v.items()} for mid, v in data.get("reaction_roles", {}).items()}
            except Exception:
                return {}
        return {}

    def save_reaction_roles(self):
        data = {"reaction_roles": {str(mid): v for mid, v in self.message_id_to_roles.items()}}
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return  # Ignora le reazioni aggiunte dal bot stesso
        if payload.message_id in self.message_id_to_roles:
            emoji = str(payload.emoji)
            role_id = self.message_id_to_roles[payload.message_id].get(emoji)
            if role_id:
                guild = self.bot.get_guild(payload.guild_id)
                if guild:
                    member = guild.get_member(payload.user_id)
                    if member:
                        role = guild.get_role(role_id)
                        if role:
                            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id in self.message_id_to_roles:
            emoji = str(payload.emoji)
            role_id = self.message_id_to_roles[payload.message_id].get(emoji)
            if role_id:
                guild = self.bot.get_guild(payload.guild_id)
                if guild:
                    member = guild.get_member(payload.user_id)
                    if member:
                        role = guild.get_role(role_id)
                        if role:
                            await member.remove_roles(role)

    @app_commands.command(name="setreactionrole", description="Imposta un reaction role su un messaggio")
    @app_commands.describe(message_id="ID del messaggio", emoji="Emoji da usare", role="Ruolo da assegnare")
    async def setreactionrole(self, interaction: discord.Interaction, message_id: str, emoji: str, role: discord.Role):
        try:
            message_id_int = int(message_id)
        except ValueError:
            await interaction.response.send_message("❌ ID messaggio non valido.", ephemeral=True)
            return
        if message_id_int not in self.message_id_to_roles:
            self.message_id_to_roles[message_id_int] = {}
        self.message_id_to_roles[message_id_int][emoji] = role.id
        self.save_reaction_roles()

        # Prova ad aggiungere la reazione al messaggio target
        try:
            channel = interaction.channel
            message = await channel.fetch_message(message_id_int)
            await message.add_reaction(emoji)
            msg = f"✅ Reaction role impostato: {emoji} → {role.mention} (reazione aggiunta al messaggio)"
        except Exception as e:
            msg = f"✅ Reaction role impostato: {emoji} → {role.mention}\n⚠️ Non sono riuscito ad aggiungere la reazione in automatico: {e}"
        await interaction.response.send_message(msg, ephemeral=True)

async def setup(bot):
    """Register the cog in the bot instance."""
    await bot.add_cog(ReactionRoles(bot))
