"""Predefined embed message sender commands."""

import discord
from discord.ext import commands
from discord import app_commands

class Messages(commands.Cog):
    """Sends template embeds to selected channels."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="message", description="Invia un messaggio embed prestabilito in un canale specifico")
    @app_commands.describe(
        tipo="Tipo di messaggio da inviare",
        canale="Canale dove inviare il messaggio"
    )
    @app_commands.choices(tipo=[
        app_commands.Choice(name="reaction_roles", value="reaction_roles"),
    ])
    async def message(self, interaction: discord.Interaction, tipo: str, canale: discord.TextChannel):
        if tipo == "reaction_roles":
            embed = discord.Embed(
                title="🎭 Reaction Roles",
                description="Reagisci con le emoji qui sotto per ottenere i ruoli corrispondenti!",
                color=0xff7900
            )
            embed.add_field(
                name=":male_sign: Maschio", 
                value="Ruolo per identificarsi come maschio", 
                inline=False
            )
            embed.add_field(
                name=":female_sign: Femmina", 
                value="Ruolo per identificarsi come femmina", 
                inline=False
            )
            embed.add_field(
                name=":transgender_symbol: Femboy", 
                value="Ruolo per identificarsi come femboy", 
                inline=False
            )
            embed.add_field(
                name=":globe_with_meridians: Ping Eventi", 
                value="Ruolo per ricevere notifiche sugli eventi", 
                inline=False
            )
            embed.add_field(
                name=":red_circle: Ping Live", 
                value="Ruolo per ricevere notifiche sulle live", 
                inline=False
            )
            embed.set_footer(text="Clicca sulle reazioni per ottenere/rimuovere i ruoli!")

        try:
            await canale.send(embed=embed)
            await interaction.response.send_message(
                f"✅ Messaggio '{tipo}' inviato con successo in {canale.mention}!",
                ephemeral=True
            )
                        
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Non ho i permessi per inviare messaggi in quel canale!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Errore nell'invio del messaggio: {e}",
                ephemeral=True
            )

async def setup(bot):
    """Register the cog in the bot instance."""
    await bot.add_cog(Messages(bot))