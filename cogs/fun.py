"""Fun and mini-game commands (facts, coin flip, rock-paper-scissors)."""

import random
import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import Context


class Choice(discord.ui.View):
    """Button view used to pick heads or tails."""

    def __init__(self) -> None:
        super().__init__()
        self.value = None

    @discord.ui.button(label="Testa", style=discord.ButtonStyle.blurple)
    async def confirm(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.value = "testa"
        self.stop()

    @discord.ui.button(label="Croce", style=discord.ButtonStyle.blurple)
    async def cancel(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.value = "croce"
        self.stop()


class RockPaperScissors(discord.ui.Select):
    """Select menu used for rock-paper-scissors choices."""

    def __init__(self) -> None:
        options = [
            discord.SelectOption(
                label="Forbici", description="Hai scelto forbici.", emoji="✂"
            ),
            discord.SelectOption(
                label="Sasso", description="Hai scelto sasso.", emoji="🪨"
            ),
            discord.SelectOption(
                label="Carta", description="Hai scelto carta.", emoji="🧻"
            ),
        ]
        super().__init__(
            placeholder="Scegli...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        choices = {
            "sasso": 0,
            "carta": 1,
            "forbici": 2,
        }
        user_choice = self.values[0].lower()
        user_choice_index = choices[user_choice]

        bot_choice = random.choice(list(choices.keys()))
        bot_choice_index = choices[bot_choice]

        result_embed = discord.Embed(color=0xBEBEFE)
        result_embed.set_author(
            name=interaction.user.name, icon_url=interaction.user.display_avatar.url
        )

        winner = (3 + user_choice_index - bot_choice_index) % 3
        if winner == 0:
            result_embed.description = f"**Questo è un pareggio!**\nHai scelto {user_choice} e anche io ho scelto {bot_choice}."
            result_embed.colour = 0xF59E42
        elif winner == 1:
            result_embed.description = f"**Hai vinto!**\nHai scelto {user_choice} e io ho scelto {bot_choice}."
            result_embed.colour = 0x57F287
        else:
            result_embed.description = f"**Hai perso**\nHai scelto {user_choice} e io ho scelto {bot_choice}."
            result_embed.colour = 0xE02B2B

        await interaction.response.edit_message(
            embed=result_embed, content=None, view=None
        )


class RockPaperScissorsView(discord.ui.View):
    """Container view for the rock-paper-scissors select menu."""

    def __init__(self) -> None:
        super().__init__()
        self.add_item(RockPaperScissors())


class Fun(commands.Cog, name="fun"):
    """General entertainment commands for the server."""

    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="randomfact", description="Racconta un fatto Random.")
    async def randomfact(self, context: Context) -> None:
        """
        Get a random fact.

        :param context: The hybrid command context.
        """
        # This will prevent your bot from stopping everything when doing a web request - see: https://discordpy.readthedocs.io/en/stable/faq.html#how-do-i-make-a-web-request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://uselessfacts.jsph.pl/random.json?language=it"
            ) as request:
                if request.status == 200:
                    data = await request.json()
                    embed = discord.Embed(description=data["text"], color=discord.Color.orange())
                else:
                    embed = discord.Embed(
                        title="Error!",
                        description="There is something wrong with the API, please try again later",
                        color=discord.Color.orange(),
                    )
                await context.send(embed=embed)

    @commands.hybrid_command(
        name="coinflip", description="Fai il lancio della moneta, ma scegli prima."
    )
    async def coinflip(self, context: Context) -> None:
        """
        Fai il lancio della moneta, ma scegli prima.

        :param context: The hybrid command context.
        """
        buttons = Choice()
        embed = discord.Embed(description="Cosa scegli?", color=discord.Color.orange())
        message = await context.send(embed=embed, view=buttons)
        await buttons.wait()  # We wait for the user to click a button.
        result = random.choice(["Testa", "Croce"])
        if buttons.value == result:
            embed = discord.Embed(
                description=f" Hai vinto!, hai scelto `{buttons.value}` e la moneta è girata in `{result}`.",
                color=discord.Color.orange(),
            )
        else:
            embed = discord.Embed(
                description=f"Woops! Hai scelto `{buttons.value}` e la moneta è girata verso `{result}`, sai più fortunato la prossima volta!",
                color=discord.Color.dark_orange(),
            )
        await message.edit(embed=embed, view=None, content=None)

    @commands.hybrid_command(
        name="rps", description="Gioca a carta sasso forbici con il bot!"
    )
    async def rock_paper_scissors(self, context: Context) -> None:
        """
        Gioca a carta sasso forbici con il bot!.

        :param context: The hybrid command context.
        """
        view = RockPaperScissorsView()
        await context.send("Please make your choice", view=view)

    


async def setup(bot) -> None:
    """Register the cog in the bot instance."""
    await bot.add_cog(Fun(bot))
