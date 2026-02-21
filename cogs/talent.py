"""Talent-show registration, scoring and leaderboard commands."""

import discord
from discord.ext import commands
from discord import app_commands
import json
import os

DATA_FILE = "./data/talent/talent_data.json"

class Talent(commands.Cog):
    """Stores users by talent roles and tracks participant scores."""

    def __init__(self, bot):
        self.bot = bot
        self.data = self.load_data()

    def load_data(self):
        if not os.path.exists(DATA_FILE):
            return {"users": {}}
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"users": {}}

    def save_data(self):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    @app_commands.command(name="talent_register", description="Registra un utente per il Talent Show")
    @app_commands.describe(user="L'utente da registrare", role="Ruolo dell'utente (Presentatore, Giudice o Partecipante)")
    @app_commands.choices(role=[
        app_commands.Choice(name="Presentatore", value="host"),
        app_commands.Choice(name="Giudice", value="judge"),
        app_commands.Choice(name="Partecipante", value="participant")
    ])
    async def register(self, interaction: discord.Interaction, user: discord.User, role: app_commands.Choice[str]):
        user_id = str(user.id)
        
        if user_id in self.data["users"]:
            await interaction.response.send_message(f"⚠️ {user.mention} è già registrato come **{self.data['users'][user_id]['role']}**.", ephemeral=True)
            return

        self.data["users"][user_id] = {
            "role": role.value,
            "points": 0,
            "name": user.name
        }
        self.save_data()
        
        role_names = {
            "host": "Presentatore 🎙️",
            "judge": "Giudice ⚖️",
            "participant": "Partecipante 🎤"
        }
        role_name = role_names.get(role.value, role.value)
        await interaction.response.send_message(f"✅ {user.mention} registrato con successo come **{role_name}**!")

    @app_commands.command(name="talent_add_points", description="Assegna punti a un partecipante (Solo Giudici)")
    @app_commands.describe(user="Il partecipante a cui dare punti", points="Numero di punti da assegnare")
    async def add_points(self, interaction: discord.Interaction, user: discord.User, points: int):
        author_id = str(interaction.user.id)
        target_id = str(user.id)

        # Check if author is a judge, host or admin
        is_authorized = False
        if author_id in self.data["users"] and self.data["users"][author_id]["role"] in ["judge", "host"]:
            is_authorized = True
        
        # Allow server admins to bypass check
        if not is_authorized and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Solo i **Giudici**, **Presentatori** o gli amministratori possono assegnare punti!", ephemeral=True)
            return

        if target_id not in self.data["users"]:
            await interaction.response.send_message(f"❌ {user.mention} non è registrato al Talent Show.", ephemeral=True)
            return

        if self.data["users"][target_id]["role"] != "participant":
            role_names = {
                "host": "Presentatore",
                "judge": "Giudice",
                "participant": "Partecipante"
            }
            current_role = role_names.get(self.data['users'][target_id]['role'], self.data['users'][target_id]['role'])
            await interaction.response.send_message(f"❌ {user.mention} non è un partecipante (è un **{current_role}**).", ephemeral=True)
            return

        self.data["users"][target_id]["points"] += points
        self.save_data()

        embed = discord.Embed(
            title="🌟 Punti Assegnati!",
            description=f"**{points}** punti per {user.mention}!\nTotale: **{self.data['users'][target_id]['points']}**",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Assegnati da {interaction.user.name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="talent_leaderboard", description="Mostra la classifica del Talent Show")
    async def leaderboard(self, interaction: discord.Interaction):
        participants = []
        for uid, info in self.data["users"].items():
            if info["role"] == "participant":
                participants.append((info["name"], info["points"]))
        
        # Sort by points descending
        participants.sort(key=lambda x: x[1], reverse=True)

        if not participants:
            await interaction.response.send_message("📭 Nessun partecipante registrato o con punti.", ephemeral=True)
            return

        leaderboard_text = ""
        for i, (name, points) in enumerate(participants):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
            leaderboard_text += f"{medal} **{name}**: {points} punti\n"

        embed = discord.Embed(
            title="🏆 Classifica Talent Show",
            description=leaderboard_text,
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="talent_list", description="Mostra tutti gli utenti registrati al Talent Show")
    async def list_users(self, interaction: discord.Interaction):
        if not self.data["users"]:
            await interaction.response.send_message("📭 Nessun utente registrato al Talent Show.", ephemeral=True)
            return

        role_icons = {
            "host": "🎙️",
            "judge": "⚖️",
            "participant": "🎤"
        }
        
        role_names = {
            "host": "Presentatore",
            "judge": "Giudice",
            "participant": "Partecipante"
        }

        # Organize users by role
        hosts = []
        judges = []
        participants = []

        for uid, info in self.data["users"].items():
            user_text = f"• **{info['name']}**"
            if info["role"] == "participant":
                user_text += f" - {info['points']} punti"
            
            if info["role"] == "host":
                hosts.append(user_text)
            elif info["role"] == "judge":
                judges.append(user_text)
            elif info["role"] == "participant":
                participants.append(user_text)

        embed = discord.Embed(
            title="📋 Utenti Registrati - Talent Show",
            color=discord.Color.blue()
        )

        if hosts:
            embed.add_field(
                name=f"{role_icons['host']} Presentatori ({len(hosts)})",
                value="\n".join(hosts),
                inline=False
            )
        
        if judges:
            embed.add_field(
                name=f"{role_icons['judge']} Giudici ({len(judges)})",
                value="\n".join(judges),
                inline=False
            )
        
        if participants:
            embed.add_field(
                name=f"{role_icons['participant']} Partecipanti ({len(participants)})",
                value="\n".join(participants),
                inline=False
            )

        embed.set_footer(text=f"Totale utenti: {len(self.data['users'])}")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    """Register the cog in the bot instance."""
    await bot.add_cog(Talent(bot))
