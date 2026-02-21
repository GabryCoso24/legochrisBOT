"""Rule management system with JSON persistence and embed publishing."""

import json
import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


class Rules(commands.Cog):
    """Create, edit, delete and publish categorized server rules."""

    RULE_TYPES = ["staff", "team", "server"]

    def __init__(self, bot):
        self.bot = bot
        self.data_path = os.path.join("data", "rules", "rules.json")
        self.sent_messages_path = os.path.join("data", "rules", "sent_messages.json")
        self.image_path = os.path.join("data", "rules", "logo", "Rules_MT.png")
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)

    def _load_rules(self):
        base = {rule_type: [] for rule_type in self.RULE_TYPES}
        if not os.path.exists(self.data_path):
            return base

        try:
            with open(self.data_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                print(f"✅ Loaded rules data: {data}")
            for rule_type in self.RULE_TYPES:
                values = data.get(rule_type, [])
                if isinstance(values, list):
                    base[rule_type] = [str(value).strip() for value in values if str(value).strip()]
                    print(f"✅ Loaded {len(base[rule_type])} rules for type '{rule_type}'")
            return base
        except Exception:
            return base

    def _save_rules(self, data):
        with open(self.data_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _load_sent_messages(self):
        if not os.path.exists(self.sent_messages_path):
            return {}

        try:
            with open(self.sent_messages_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict):
                return data
            return {}
        except Exception:
            return {}

    def _save_sent_messages(self, data):
        with open(self.sent_messages_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _sanitize_type(self, rule_type: str):
        value = (rule_type or "").lower().strip()
        if value not in self.RULE_TYPES:
            return None
        return value

    def _collect_bulk_rules(self, *rules: Optional[str]):
        return [rule.strip() for rule in rules if isinstance(rule, str) and rule.strip()]

    def _parse_multiline_rules(self, text: str):
        normalized = text.replace("|", "\n")
        return [line.strip() for line in normalized.splitlines() if line.strip()]

    @app_commands.command(name="add_rule", description="Aggiunge una regola singola")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(tipo="Tipo regole", rule="Testo della regola")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="staff", value="staff"),
        app_commands.Choice(name="team", value="team"),
        app_commands.Choice(name="server", value="server"),
    ])
    async def add_rule(self, interaction: discord.Interaction, tipo: str, rule: str):
        rule_type = self._sanitize_type(tipo)
        if not rule_type:
            return await interaction.response.send_message("❌ Tipo non valido. Usa: staff, team o server.", ephemeral=True)

        rules = self._load_rules()
        rules[rule_type].append(rule.strip())
        self._save_rules(rules)
        await interaction.response.send_message(
            f"✅ Regola aggiunta in **{rule_type}** (totale: {len(rules[rule_type])}).",
            ephemeral=True,
        )

    @app_commands.command(name="add_rules", description="Aggiunge più regole in una volta")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        tipo="Tipo regole",
        rule1="Regola 1",
        rule2="Regola 2",
        rule3="Regola 3",
        rule4="Regola 4",
        rule5="Regola 5",
        rule6="Regola 6",
        rule7="Regola 7",
        rule8="Regola 8",
        rule9="Regola 9",
        rule10="Regola 10",
    )
    @app_commands.choices(tipo=[
        app_commands.Choice(name="staff", value="staff"),
        app_commands.Choice(name="team", value="team"),
        app_commands.Choice(name="server", value="server"),
    ])
    async def add_rules(
        self,
        interaction: discord.Interaction,
        tipo: str,
        rule1: str,
        rule2: Optional[str] = None,
        rule3: Optional[str] = None,
        rule4: Optional[str] = None,
        rule5: Optional[str] = None,
        rule6: Optional[str] = None,
        rule7: Optional[str] = None,
        rule8: Optional[str] = None,
        rule9: Optional[str] = None,
        rule10: Optional[str] = None,
    ):
        rule_type = self._sanitize_type(tipo)
        if not rule_type:
            return await interaction.response.send_message("❌ Tipo non valido. Usa: staff, team o server.", ephemeral=True)

        new_rules = self._collect_bulk_rules(rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9, rule10)
        if not new_rules:
            return await interaction.response.send_message("❌ Devi inserire almeno una regola valida.", ephemeral=True)

        rules = self._load_rules()
        rules[rule_type].extend(new_rules)
        self._save_rules(rules)
        await interaction.response.send_message(
            f"✅ Aggiunte **{len(new_rules)}** regole in **{rule_type}** (totale: {len(rules[rule_type])}).",
            ephemeral=True,
        )

    @app_commands.command(name="remove_rule", description="Rimuove una regola in base al numero")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(tipo="Tipo regole", indice="Numero regola (partendo da 1)")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="staff", value="staff"),
        app_commands.Choice(name="team", value="team"),
        app_commands.Choice(name="server", value="server"),
    ])
    async def remove_rule(self, interaction: discord.Interaction, tipo: str, indice: int):
        rule_type = self._sanitize_type(tipo)
        if not rule_type:
            return await interaction.response.send_message("❌ Tipo non valido. Usa: staff, team o server.", ephemeral=True)

        rules = self._load_rules()
        if indice < 1 or indice > len(rules[rule_type]):
            return await interaction.response.send_message("❌ Numero regola non valido.", ephemeral=True)

        removed = rules[rule_type].pop(indice - 1)
        self._save_rules(rules)
        await interaction.response.send_message(
            f"✅ Rimossa regola #{indice} da **{rule_type}**: {removed}",
            ephemeral=True,
        )

    @app_commands.command(name="edit_rule", description="Modifica una regola specifica")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(tipo="Tipo regole", indice="Numero regola (partendo da 1)", nuova_rule="Nuovo testo")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="staff", value="staff"),
        app_commands.Choice(name="team", value="team"),
        app_commands.Choice(name="server", value="server"),
    ])
    async def edit_rule(self, interaction: discord.Interaction, tipo: str, indice: int, nuova_rule: str):
        rule_type = self._sanitize_type(tipo)
        if not rule_type:
            return await interaction.response.send_message("❌ Tipo non valido. Usa: staff, team o server.", ephemeral=True)

        rules = self._load_rules()
        if indice < 1 or indice > len(rules[rule_type]):
            return await interaction.response.send_message("❌ Numero regola non valido.", ephemeral=True)

        old_value = rules[rule_type][indice - 1]
        rules[rule_type][indice - 1] = nuova_rule.strip()
        self._save_rules(rules)
        await interaction.response.send_message(
            f"✅ Modificata regola #{indice} in **{rule_type}**.\nPrima: {old_value}\nDopo: {nuova_rule.strip()}",
            ephemeral=True,
        )

    @app_commands.command(name="edit_rules", description="Sostituisce l'intera lista regole (fino a 10 input)")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        tipo="Tipo regole",
        rule1="Regola 1",
        rule2="Regola 2",
        rule3="Regola 3",
        rule4="Regola 4",
        rule5="Regola 5",
        rule6="Regola 6",
        rule7="Regola 7",
        rule8="Regola 8",
        rule9="Regola 9",
        rule10="Regola 10",
    )
    @app_commands.choices(tipo=[
        app_commands.Choice(name="staff", value="staff"),
        app_commands.Choice(name="team", value="team"),
        app_commands.Choice(name="server", value="server"),
    ])
    async def edit_rules(
        self,
        interaction: discord.Interaction,
        tipo: str,
        rule1: str,
        rule2: Optional[str] = None,
        rule3: Optional[str] = None,
        rule4: Optional[str] = None,
        rule5: Optional[str] = None,
        rule6: Optional[str] = None,
        rule7: Optional[str] = None,
        rule8: Optional[str] = None,
        rule9: Optional[str] = None,
        rule10: Optional[str] = None,
    ):
        rule_type = self._sanitize_type(tipo)
        if not rule_type:
            return await interaction.response.send_message("❌ Tipo non valido. Usa: staff, team o server.", ephemeral=True)

        new_rules = self._collect_bulk_rules(rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9, rule10)
        if not new_rules:
            return await interaction.response.send_message("❌ Devi inserire almeno una regola valida.", ephemeral=True)

        rules = self._load_rules()
        rules[rule_type] = new_rules
        self._save_rules(rules)
        await interaction.response.send_message(
            f"✅ Lista **{rule_type}** aggiornata con **{len(new_rules)}** regole.",
            ephemeral=True,
        )

    @app_commands.command(name="create_rules", description="Crea/Sovrascrive le regole da testo multi-linea")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(tipo="Tipo regole", rules_text="Una regola per riga (oppure separa con |)")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="staff", value="staff"),
        app_commands.Choice(name="team", value="team"),
        app_commands.Choice(name="server", value="server"),
    ])
    async def create_rules(self, interaction: discord.Interaction, tipo: str, rules_text: str):
        rule_type = self._sanitize_type(tipo)
        if not rule_type:
            return await interaction.response.send_message("❌ Tipo non valido. Usa: staff, team o server.", ephemeral=True)

        new_rules = self._parse_multiline_rules(rules_text)
        if not new_rules:
            return await interaction.response.send_message("❌ Nessuna regola valida trovata nel testo.", ephemeral=True)

        rules = self._load_rules()
        rules[rule_type] = new_rules
        self._save_rules(rules)
        await interaction.response.send_message(
            f"✅ Create **{len(new_rules)}** regole per **{rule_type}**.",
            ephemeral=True,
        )

    @app_commands.command(name="send_rules", description="Invia immagine + embed regole")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        tipo="Tipo regole",
        canale="Canale dove inviare il messaggio",
        titolo="Titolo personalizzato dell'embed",
    )
    @app_commands.choices(tipo=[
        app_commands.Choice(name="staff", value="staff"),
        app_commands.Choice(name="team", value="team"),
        app_commands.Choice(name="server", value="server"),
    ])
    async def send_rules(
        self,
        interaction: discord.Interaction,
        tipo: str,
        canale: discord.TextChannel,
        titolo: Optional[str] = None,
    ):
        rule_type = self._sanitize_type(tipo)
        if not rule_type:
            return await interaction.response.send_message("❌ Tipo non valido. Usa: staff, team o server.", ephemeral=True)

        if interaction.guild is None:
            return await interaction.response.send_message("❌ Questo comando può essere usato solo in un server.", ephemeral=True)

        rules = self._load_rules()
        target_rules = rules.get(rule_type, [])
        if not target_rules:
            return await interaction.response.send_message(
                f"❌ Nessuna regola configurata per **{rule_type}**.",
                ephemeral=True,
            )

        description = "\n".join([f"- {text}" for text in target_rules])
        embed_title = (titolo or "").strip() or f"📜 Rules - {rule_type.capitalize()}"
        embed = discord.Embed(
            title=embed_title,
            description=description,
            color=0xff7900,
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text=f"Grazie per aver letto le regole {rule_type}. Buona permanenza!")

        guild_id = str(interaction.guild.id)
        sent_messages = self._load_sent_messages()
        previous = sent_messages.get(guild_id, {}).get(rule_type)

        if previous:
            old_channel_id = previous.get("channel_id")
            old_embed_message_id = previous.get("embed_message_id")
            old_image_message_id = previous.get("image_message_id")
            old_legacy_message_id = previous.get("message_id")
            if isinstance(old_channel_id, int):
                old_channel = interaction.guild.get_channel(old_channel_id)
                if old_channel is None:
                    old_channel = self.bot.get_channel(old_channel_id)
                if isinstance(old_channel, discord.TextChannel):
                    for old_message_id in [old_image_message_id, old_embed_message_id, old_legacy_message_id]:
                        if not isinstance(old_message_id, int):
                            continue
                        try:
                            old_message = await old_channel.fetch_message(old_message_id)
                            await old_message.delete()
                        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                            pass

        sent_image_message = None
        if os.path.exists(self.image_path):
            file = discord.File(self.image_path, filename="Rules_MT.png")
            sent_image_message = await canale.send(file=file)

        sent_embed_message = await canale.send(embed=embed)

        guild_store = sent_messages.setdefault(guild_id, {})
        guild_store[rule_type] = {
            "channel_id": canale.id,
            "image_message_id": sent_image_message.id if sent_image_message else None,
            "embed_message_id": sent_embed_message.id,
        }
        self._save_sent_messages(sent_messages)

        await interaction.response.send_message(
            f"✅ Regole **{rule_type}** inviate in {canale.mention}. Se esisteva un vecchio messaggio, è stato sostituito.",
            ephemeral=True,
        )


async def setup(bot):
    """Register the cog in the bot instance."""
    await bot.add_cog(Rules(bot))
