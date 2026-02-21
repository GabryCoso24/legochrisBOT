"""Legacy prefix-based fun/media commands kept for backward compatibility."""

import discord
from discord.ext import commands
import random


client = commands.Bot(command_prefix= '!', intents=discord.Intents.all())



class legacy(commands.Cog):
    """Collection of legacy text-command handlers."""

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("i legacy commands funzionano")

    @commands.command()
    async def nsfw(self, ctx):
        await ctx.send("DAMN BROO!!", file = discord.File("./media/1030.mp4"))

    @commands.command()
    async def CATANZARO(self, ctx):
        await ctx.send(file = discord.File('./media/monkeys dancing.mp4'))    

    @commands.command()
    async def smurf(self, ctx):
        for smurfcat in range(69):
            await ctx.send(f"|| {smurfcat} ||",file = discord.File('./media/smurf.mp4'))    

    @commands.command()
    async def that_is_no_good_idea(self, ctx):
        await ctx.send(file = discord.File('./media/Undertale Last Breath Phase 3 Full Animation by MolingXingKong.mp4'))    

    @commands.command()
    async def therock(self, ctx):
        await ctx.send(file = discord.File('./media/papyrusxtherock.mp4'))

    @commands.command()
    async def fnafmovie(self, ctx):
        await ctx.send(file = discord.File('./media/fnaffilm.mp4'))    

    @commands.command()
    async def leone(self, ctx):
        await ctx.send(file = discord.File('./media/leone.mp4'))    

    @commands.command()
    async def sans(self, ctx):
        await ctx.send(file = discord.File('./media/sans.mp4'))       

    @commands.command()
    async def ULB(self, ctx):
        await ctx.send(file = discord.File('./media/sigma_male-1-1.mp4'))

    @commands.command()
    async def balls(self, ctx):
        await ctx.send(file = discord.File('./media/Balls.mp4'))

    @commands.command()
    async def ping(self, ctx):
        client_latency = round(self.client.latency * 1000)
        embed_message = discord.Embed(title=f"PONG! {client_latency} ms :ping_pong:!", description=(""), color=discord.Color.dark_orange())        
        await ctx.send(embed = embed_message)

    @commands.command()
    async def Story(self, ctx):
        await ctx.send("...una sera un vecchio saggio disse: *Ti sfido su **FORTNITE***" , file= discord.File("./media/salvini.png"))

    @commands.command()
    async def userinfo(self, ctx , member: discord.Member=None):
        if member is None:
            member = ctx.author
        elif member is not None:
            member = member

        info_embed = discord.Embed(title=f"{member.name}'s Information", description=(f"All information about {member.name}"), color=discord.Color.orange())
        info_embed.set_thumbnail(url=member.avatar)
        info_embed.add_field(name="Name:", value=member.name, inline=False)
        info_embed.add_field(name="Nick Name:", value=member.display_name, inline=False)
        info_embed.add_field(name="Discriminator:", value=member.discriminator, inline=False)
        info_embed.add_field(name="ID:", value=member.id, inline=False)
        info_embed.add_field(name="Top Role:", value=member.top_role, inline=False)
        info_embed.add_field(name="Status:", value=member.status, inline=False)
        info_embed.add_field(name="Bot User?", value=member.bot, inline=False)
        info_embed.add_field(name="Creation Date:", value=member.created_at.__format__("%A, %d. %B %Y @ %H:%M:%S"), inline=False)
        await ctx.send(embed = info_embed)

    @commands.command()
    async def inverti_testo(self, ctx, *, testo: str):
        testo_invertito = testo[::-1]
        await ctx.send(f"Testo invertito: {testo_invertito}")
        await ctx.message.delete()

async def setup(client):
    """Register the cog in the bot instance."""
    await client.add_cog(legacy(client))