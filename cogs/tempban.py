"""Temporary ban system with persistence and automatic unban scheduling."""

import discord
from discord.ext import commands
from discord import app_commands
import re
from asyncio import sleep


import json
import os
from datetime import datetime, timedelta

class TempBan(commands.Cog):
    """Provides tempban lifecycle commands and storage helpers."""

    @app_commands.command(name="listtempbans", description="Mostra tutti i tempban attivi e scaduti")
    async def listtempbans(self, interaction: discord.Interaction):
        lines = []
        # Attivi
        for uid, (guild_id, _, end_time) in self.tempbans.items():
            lines.append(f"🟠 <@{uid}>\n(**ID:** `{uid}`)\n**Fine:** <t:{int(end_time.timestamp())}:f>\n**Stato:** ATTIVO\n")
        # Scaduti
        if hasattr(self, "expired_tempbans"):
            for uid, info in self.expired_tempbans.items():
                lines.append(f"🟠 <@{uid}>\n(**ID:** `{uid}`)\n**Fine:** <t:{int(datetime.fromisoformat(info['end_time']).timestamp())}:f>\n**Stato:** SCADUTO\n")
        if not lines:
            await interaction.response.send_message("Nessun tempban registrato.")
            return
        # Paginazione se >20
        chunk_size = 20
        for i in range(0, len(lines), chunk_size):
            chunk = lines[i:i+chunk_size]
            embed = discord.Embed(title="Tempban registrati", description="\n".join(chunk), color=discord.Color.orange())
            await interaction.response.send_message(embed=embed) if i == 0 else await interaction.followup.send(embed=embed)
    def __init__(self, client):
        self.client = client
        self.data_path = os.path.join("data", "tempban", "tempbans.json")
        self.tempbans = {}  # {user_id: (guild_id, task, end_time)}
        self._load_tempbans()

    def _save_tempbans(self):
        # Salva sia attivi che scaduti
        all_tempbans = {}
        # Attivi
        for uid, (gid, _, et) in self.tempbans.items():
            all_tempbans[str(uid)] = {"guild_id": gid, "end_time": et.isoformat(), "expired": False}
        # Scaduti
        if hasattr(self, "expired_tempbans"):
            for uid, info in self.expired_tempbans.items():
                all_tempbans[str(uid)] = info
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump({"tempbans": all_tempbans}, f, ensure_ascii=False, indent=2)

    def _load_tempbans(self):
        self.expired_tempbans = {}
        if not os.path.exists(self.data_path):
            return
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            now = datetime.utcnow()
            for uid, v in data.get("tempbans", {}).items():
                guild_id = v["guild_id"]
                end_time = datetime.fromisoformat(v["end_time"])
                expired = v.get("expired", False)
                seconds_left = (end_time - now).total_seconds()
                if not expired and seconds_left > 0:
                    self._schedule_restore(int(uid), guild_id, end_time, seconds_left)
                else:
                    self.expired_tempbans[str(uid)] = {"guild_id": guild_id, "end_time": end_time.isoformat(), "expired": True}
        except Exception:
            pass

    def _schedule_restore(self, user_id, guild_id, end_time, seconds_left):
        async def restore_task():
            await sleep(seconds_left)
            guild = self.client.get_guild(guild_id)
            if guild:
                user = discord.Object(id=user_id)
                try:
                    await guild.unban(user)
                except Exception:
                    pass
            # Sposta nei tempban scaduti
            if not hasattr(self, "expired_tempbans"):
                self.expired_tempbans = {}
            self.expired_tempbans[str(user_id)] = {"guild_id": guild_id, "end_time": end_time.isoformat(), "expired": True}
            self.tempbans.pop(user_id, None)
            self._save_tempbans()
        task = self.client.loop.create_task(restore_task())
        self.tempbans[user_id] = (guild_id, task, end_time)
        def _schedule_restore(self, user_id, guild_id, end_time, seconds_left):
            async def restore_task():
                await sleep(seconds_left)
                guild = self.client.get_guild(guild_id)
                if guild:
                    user = discord.Object(id=user_id)
                    try:
                        await guild.unban(user)
                    except Exception:
                        pass
                # Sposta nei tempban scaduti
                if not hasattr(self, "expired_tempbans"):
                    self.expired_tempbans = {}
                self.expired_tempbans[str(user_id)] = {"guild_id": guild_id, "end_time": end_time.isoformat(), "expired": True}
                self.tempbans.pop(user_id, None)
                self._save_tempbans()
            task = self.client.loop.create_task(restore_task())
            self.tempbans[user_id] = (guild_id, task, end_time)

    @app_commands.command(name="tempban", description="Temporarily ban a user")
    @app_commands.default_permissions(ban_members=True)
    async def tempban(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "Nessun motivo fornito"):
        guild = interaction.guild
        duration_seconds = self.parse_duration(duration)
        if duration_seconds is None:
            await interaction.response.send_message("Formato di durata non valido. Utilizza il formato corretto come '1d2h30m'.")
            return
        await member.ban(reason=reason)
        embed = discord.Embed(title="Temp Ban", description=f"{member.mention} è stato bannato da {interaction.user.mention} per {duration}.", color=discord.Color.orange())
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar)
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text="TempBan", icon_url=self.client.user.avatar)
        await interaction.response.send_message(embed=embed)
        end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
        task = self.client.loop.create_task(self._tempban_task(guild, member, duration_seconds, interaction, end_time))
        self.tempbans[member.id] = (guild.id, task, end_time)
        self._save_tempbans()

    async def _tempban_task(self, guild, member, duration_seconds, interaction, end_time):
        await sleep(duration_seconds)
        await guild.unban(member)
        embed = discord.Embed(title="Temp Ban", description=f"{member.mention} è stato sbannato automaticamente perché il tempo del ban è finito.", color=discord.Color.orange())
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar)
        embed.set_footer(text="TempBan", icon_url=self.client.user.avatar)
        try:
            await interaction.edit_original_response(embed=embed)
        except Exception:
            pass
        self.tempbans.pop(member.id, None)
        self._save_tempbans()

    @app_commands.command(name="tempban_modify", description="Modifica la durata di un tempban attivo tramite ID utente")
    @app_commands.default_permissions(ban_members=True)
    async def tempban_modify(self, interaction: discord.Interaction, user_id: str, new_duration: str):
        try:
            uid = int(user_id)
        except Exception:
            await interaction.response.send_message("ID utente non valido.", ephemeral=True)
            return
        if uid not in self.tempbans:
            await interaction.response.send_message("❌ Nessun tempban attivo per questo utente.", ephemeral=True)
            return
        _, task, _ = self.tempbans[uid]
        task.cancel()
        duration_seconds = self.parse_duration(new_duration)
        if duration_seconds is None:
            await interaction.response.send_message("Formato di durata non valido.", ephemeral=True)
            return
        guild = interaction.guild
        # Usa solo l'ID utente, anche se non è più nel server
        end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
        async def unban_task():
            await sleep(duration_seconds)
            user = discord.Object(id=uid)
            try:
                await guild.unban(user)
            except Exception:
                pass
            if not hasattr(self, "expired_tempbans"):
                self.expired_tempbans = {}
            self.expired_tempbans[str(uid)] = {"guild_id": guild.id, "end_time": end_time.isoformat(), "expired": True}
            self.tempbans.pop(uid, None)
            self._save_tempbans()
        new_task = self.client.loop.create_task(unban_task())
        self.tempbans[uid] = (guild.id, new_task, end_time)
        self._save_tempbans()
        await interaction.response.send_message(f"✅ Durata del tempban aggiornata a {new_duration}.", ephemeral=True)

    @app_commands.command(name="tempban_remove", description="Rimuovi un tempban attivo tramite ID utente e sbanna subito")
    @app_commands.default_permissions(ban_members=True)
    async def tempban_remove(self, interaction: discord.Interaction, user_id: str):
        try:
            uid = int(user_id)
        except Exception:
            await interaction.response.send_message("ID utente non valido.", ephemeral=True)
            return
        if uid not in self.tempbans:
            await interaction.response.send_message("❌ Nessun tempban attivo per questo utente.", ephemeral=True)
            return
        _, task, _ = self.tempbans[uid]
        task.cancel()
        guild = interaction.guild
        user = discord.Object(id=uid)
        await guild.unban(user)
        # Sposta nei tempban scaduti
        if not hasattr(self, "expired_tempbans"):
            self.expired_tempbans = {}
        self.expired_tempbans[str(uid)] = {"guild_id": guild.id, "end_time": datetime.utcnow().isoformat(), "expired": True}
        self.tempbans.pop(uid, None)
        self._save_tempbans()
        await interaction.response.send_message(f"✅ Tempban rimosso e utente sbannato subito.", ephemeral=True)

    def parse_duration(self, duration):
        pattern = r'(\d+)([smhdwMy])'
        matches = re.findall(pattern, duration)
        if not matches:
            return None
        total_seconds = 0
        for match in matches:
            value, unit = int(match[0]), match[1]
            if unit == 's':
                total_seconds += value
            elif unit == 'm':
                total_seconds += value * 60
            elif unit == 'h':
                total_seconds += value * 60 * 60
            elif unit == 'd':
                total_seconds += value * 24 * 60 * 60
            elif unit == 'w':
                total_seconds += value * 7 * 24 * 60 * 60
            elif unit == 'M':
                total_seconds += value * 30 * 24 * 60 * 60
            elif unit == 'y':
                total_seconds += value * 365 * 24 * 60 * 60
        return total_seconds

async def setup(client):
    """Register the cog in the bot instance."""
    await client.add_cog(TempBan(client))
