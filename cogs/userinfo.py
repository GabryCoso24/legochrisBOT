"""User information command with profile and account metadata."""

import discord
from discord.ext import commands
from discord import app_commands
import random

class UserInfo(commands.Cog):
    """Shows extended information about a server member."""

    def __init__(self, client):
        self.client = client

    @app_commands.command(name="userinfo", description="Get a user Information")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        if member is None:
            member = interaction.user
        jojo_chance = random.randint(1, 200)
        jojo_stands = [
            "Star Platinum", "Magician's Red", "Hermit Purple", "Hierophant Green", "Silver Chariot", "The Fool", "Yellow Temperance", "Hanged Man", "Emperor", "Empress", "The Tower", "Strength", "Ebony Devil", "Yellow Submarine", "Santana", "Talking Head", "Spice Girl", "The World", "Crazy Diamond", "Killer Queen", "Echoes", "Star Platinum: The World", "Hierophant Green: The Emerald Splash", "Tower of Gray", "Dark Blue Moon", "Ebony Devil", "Yellow Temperance: Rubber Soul", "Hanged Man", "Emperor and Empress: Nena", "Wheel of Fortune", "Justice", "Lovers", "The Sun", "Death Thirteen", "Judgement", "Geb", "Khnum", "Tohth", "Anubis", "Bastet", "Sethan", "Osiris", "Horus", "Atum", "Heaven's Door", "Enigma", "Cheap Trick", "Achtung Baby", "The Hand", "Echoes", "Crazy Diamond", "Killer Queen", "Killer Queen: Bites the Dust", "Gold Experience", "Sticky Fingers", "Moody Blues", "Sex Pistols", "Aerosmith", "Purple Haze", "King Crimson", "Black Sabbath", "White Album", "Beach Boy", "Grateful Dead", "Baby Face", "Kraft Work", "Soft Machine", "Clash", "Talking Head", "Notorious B.I.G", "Spice Girl", "Metallica", "Green Day", "Oasis", "Rolling Stones", "Squalo and Tiziano", "Stone Free", "Kiss", "Burning Down the House", "Foo Fighters", "Weather Report", "Diver Down", "Manhattan Transfer", "Jumpin' Jack Flash", "Marilyn Manson", "C-Moon", "Made in Heaven", "Tusk", "Cream Starter", "Dirty Deeds Done Dirt Cheap (D4C)", "Scary Monsters", "Mandom", "Catch the Rainbow", "Sugar Mountain", "Tubular Bells", "20th Century Boy", "Civil War", "Tattoo You!", "In a Silent Way", "Hey Ya!", "Chocolate Disco", "Wired", "Filthy Acts at a Reasonable Price (Love Train)"
        ]
        info_embed = discord.Embed(title=f"{member.name}'s Information", description=(f"All information about {member.name}"), color=discord.Color.purple())
        info_embed.set_thumbnail(url=member.avatar)
        info_embed.add_field(name="Name:", value=member.name, inline=False)
        info_embed.add_field(name="Nick Name:", value=member.display_name, inline=False)
        info_embed.add_field(name="Status:", value=member.status, inline=False)
        if jojo_chance == 1:
            info_embed.add_field(name="Jojo's Stand:", value=random.choice(jojo_stands), inline=False)
        if member.discriminator != "0":
            info_embed.add_field(name="Discriminator:", value=f"```{member.discriminator}```", inline=False)
        info_embed.add_field(name="ID:", value=member.id, inline=False)
        if member.top_role.name == "@everyone":
            info_embed.add_field(name="Top Role:", value="None", inline=False)
        else:
            info_embed.add_field(name="Top Role:", value=member.top_role.mention, inline=False)
        info_embed.add_field(name="Bot User?", value=member.bot, inline=False)
        info_embed.add_field(name="Join Server Date:", value=member.joined_at.__format__("%A %d %B %Y"), inline=False)
        info_embed.add_field(name="Creation Date:", value=member.created_at.__format__("%A %d %B %Y"), inline=False)
        info_embed.set_footer(text="Users Informations", icon_url=self.client.user.avatar)
        await interaction.response.send_message(embed=info_embed)

async def setup(client):
    """Register the cog in the bot instance."""
    await client.add_cog(UserInfo(client))
