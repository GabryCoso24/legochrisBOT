"""Ticketing system with category routing, claim/close actions and transcripts."""

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View, Button
import os
import json
import asyncio
import datetime
from pathlib import Path

class Tickets(commands.Cog):
    """Implements persistent ticket creation, claiming, closing and logging."""

    TICKET_CATEGORY_NAME = "🎫 | ----- | Supporto | ----- | 🎫"
    TICKET_CHANNEL_NAME = "「🎫」ticket"
    TICKET_CHANNEL_LOGS = "「📥」ticket-logs"
    TICKET_CATEGORY_LOGS = "🔧 | ----- | Logs | ----- | 🔧"
    STAFF_ROLE_ID = 1174748519660269629

    DATA_FILE = "./data/tickets/persistent_data.json"
    TICKET_FILE = "./data/tickets/tickets.json"
    ID_FILE = "./data/tickets/ids.json"

    category_map = {
        "🌍 Candidatura Evento": "Candidatura Evento",
        "📹 Candidatura Content Creator": "Candidatura Content Creator",
        "🔧 Candidatura Staff": "Candidatura Staff",
        "❓ Aiuto o info": "Aiuto o info",
        "🎫 Segnalazione di uno o più utenti": "Segnalazione di uno o più utenti",
        "❕ Altro...": "Altro"
    }

    def __init__(self, bot):
        self.bot = bot
        # Assicurati che le directory necessarie esistano
        os.makedirs("./data/tickets/logs", exist_ok=True)
        os.makedirs("./data/tickets", exist_ok=True)

    async def delete_void_ticket_category(self, guild):
        try:
            for category in self.category_map.values():
                category = discord.utils.get(guild.categories, name=category)
                if category is not None and len(category.channels) == 0:
                    await category.delete()
        except Exception as e:
            print(f"Errore durante l'eliminazione della categoria: {e}")

    def load_data(self):
        try:
            if os.path.exists(self.DATA_FILE):
                with open(self.DATA_FILE, "r") as file:
                    return json.load(file)
            return {}
        except Exception as e:
            print(f"Errore durante il caricamento dei dati: {e}")
            return {}

    def save_data(self, data):
        try:
            with open(self.DATA_FILE, "w") as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            print(f"Errore durante il salvataggio dei dati: {e}")

    def load_ticket_data(self):
        try:
            if os.path.exists(self.TICKET_FILE):
                with open(self.TICKET_FILE, "r") as file:
                    return json.load(file)
            return {}
        except Exception as e:
            print(f"Errore durante il caricamento dei dati dei ticket: {e}")
            return {}

    def save_ticket_data(self, ticket_data):
        try:
            with open(self.TICKET_FILE, "w") as file:
                json.dump(ticket_data, file, indent=4)
        except Exception as e:
            print(f"Errore durante il salvataggio dei dati dei ticket: {e}")

    def load_ids(self):
        try:
            if os.path.exists(self.ID_FILE):
                with open(self.ID_FILE, "r") as file:
                    return json.load(file)
            return {}
        except Exception as e:
            print(f"Errore durante il caricamento degli ID: {e}")
            return {}

    def save_ids(self, ids):
        try:
            with open(self.ID_FILE, "w") as file:
                json.dump(ids, file, indent=4)
        except Exception as e:
            print(f"Errore durante il salvataggio degli ID: {e}")

    def get_current_ticket_id(self):
        ids = self.load_ids()
        return ids.get("ticket_id", 0)

    def increment_ticket_id(self):
        ids = self.load_ids()
        ticket_id = ids.get("ticket_id", 0) + 1
        ids["ticket_id"] = ticket_id
        self.save_ids(ids)
        return ticket_id

    async def generate_transcript(self, channel):
        try:
            transcript_file = f"./data/tickets/logs/transcript_{channel.id}.txt"
            
            with open(transcript_file, "w", encoding="utf-8") as file:
                messages = [message async for message in channel.history(limit=None)]
                for message in reversed(messages):
                    file.write(f"{message.author.name}: {message.content}\n")
                    if message.embeds:
                        for embed in message.embeds:
                            file.write(f"Embed: {embed.title}\n")
                    file.write("\n")
            
            return transcript_file
        except Exception as e:
            print(f"Errore durante la generazione del transcript: {e}")
            return None

    class ClaimButton(Button):
        def __init__(self, cog, ticket_channel, user):
            super().__init__(label="🙋Claim", style=discord.ButtonStyle.green, custom_id="claim")
            self.cog = cog
            self.ticket_channel = ticket_channel
            self.user = user

        async def callback(self, interaction: discord.Interaction):
            try:
                staff_role = interaction.guild.get_role(self.cog.STAFF_ROLE_ID)
                if staff_role not in interaction.user.roles:
                    await interaction.response.send_message("Non hai i permessi per claimare i ticket", ephemeral=True)
                    return

                await self.ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
                await self.ticket_channel.set_permissions(self.user, read_messages=True, send_messages=True)
                await self.ticket_channel.set_permissions(staff_role, read_messages=True, send_messages=False)

                self.view.remove_item(self)
                await interaction.message.edit(view=self.view)

                ticket_data = self.cog.load_ticket_data()
                for ticket_name, ticket_info in ticket_data.items():
                    if ticket_info.get("channel_id") == self.ticket_channel.id:
                        ticket_info["claimed_by"] = interaction.user.mention
                        break
                self.cog.save_ticket_data(ticket_data)

                await interaction.response.send_message(f"Ticket claimato da {interaction.user.mention}")
            except Exception as e:
                print(f"Errore durante il claim del ticket: {e}")
                await interaction.response.send_message("Si è verificato un errore durante il claim del ticket", ephemeral=True)

    class CloseWithReasonButton(Button):
        def __init__(self, cog, ticket_channel, user_id):
            super().__init__(label="🔒Chiudi", style=discord.ButtonStyle.danger, custom_id="close_with_reason")
            self.cog = cog
            self.ticket_channel = ticket_channel
            self.user_id = user_id

        async def callback(self, interaction: discord.Interaction):
            try:
                staff_role = interaction.guild.get_role(self.cog.STAFF_ROLE_ID)
                if staff_role not in interaction.user.roles:
                    await interaction.response.send_message("Non hai i permessi per chiudere i ticket", ephemeral=True)
                    return

                await interaction.response.send_modal(Tickets.ReasonModal(self.cog, self.ticket_channel, self.user_id))
            except Exception as e:
                print(f"Errore durante l'apertura del modal di chiusura: {e}")
                await interaction.response.send_message("Si è verificato un errore durante l'apertura del modal", ephemeral=True)

    class ReasonModal(discord.ui.Modal, title="Chiudi Ticket"):
        reason = discord.ui.TextInput(label="Motivo", style=discord.TextStyle.long)

        def __init__(self, cog, ticket_channel, user_id):
            super().__init__()
            self.cog = cog
            self.ticket_channel = ticket_channel
            self.user_id = user_id

        async def on_submit(self, interaction: discord.Interaction):
            try:
                await interaction.response.send_message(f"Ticket Chiuso con Motivo: {self.reason.value}", ephemeral=True)

                log_channel = discord.utils.get(interaction.guild.channels, name=self.cog.TICKET_CHANNEL_LOGS)
                if log_channel:
                    ticket_id = self.cog.get_current_ticket_id()
                    ticket_data = self.cog.load_ticket_data()
                    created_at = "Unknown"
                    closed_at = "Unknown"
                    claimed_by = None
                    closed_by = interaction.user.mention
                    user_id = None
                    
                    for ticket_name, ticket_info in ticket_data.items():
                        if ticket_info.get("channel_id") == self.ticket_channel.id:
                            claimed_by = ticket_info.get("claimed_by", "Not Claimed")
                            created_at = ticket_info.get("created_at", "Unknown")
                            ticket_info["closed_by"] = closed_by
                            ticket_info["closed_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                            closed_at = ticket_info["closed_at"]
                            ticket_info["reason"] = self.reason.value
                            user_id = ticket_info.get("user_id")
                            try:
                                user = await interaction.guild.fetch_member(user_id)
                                opened_by = user.mention
                            except discord.NotFound:
                                opened_by = f"ID Utente: {user_id} (potrebbe aver lasciato il server)"
                            break
                    self.cog.save_ticket_data(ticket_data)

                    embed = discord.Embed(
                        title=":ticket: Ticket Chiuso",
                        color=discord.Color(0xff7900)
                    )
                    embed.add_field(name="Ticket ID", value=ticket_id, inline=True)
                    embed.add_field(name="Aperto da", value=opened_by, inline=True)
                    embed.add_field(name="Chiuso da", value=closed_by, inline=True)
                    embed.add_field(name="Claimato da", value=claimed_by, inline=True)
                    embed.add_field(name="Aperto il", value=created_at, inline=True)
                    embed.add_field(name="Chiuso il", value=closed_at, inline=True)
                    embed.add_field(name="Motivo", value=self.reason.value, inline=False)
                    embed.set_footer(text="LegoChris Ticket System", icon_url=interaction.guild.icon.url)
                    embed.set_thumbnail(url=interaction.guild.icon.url)

                    transcript_file = await self.cog.generate_transcript(self.ticket_channel)
                    if transcript_file:
                        await log_channel.send(embed=embed)
                        with open(transcript_file, "rb") as file:
                            await log_channel.send(file=discord.File(file, filename=f"transcript_{self.ticket_channel.id}.txt"))
                        # Pulisci il file dopo l'uso
                        try:
                            os.remove(transcript_file)
                        except Exception as e:
                            print(f"Errore durante la pulizia del file transcript: {e}")
                    else:
                        await log_channel.send(embed=embed)
                        await log_channel.send("⚠️ Impossibile generare il transcript del ticket")

                await self.ticket_channel.delete()
                await self.cog.delete_void_ticket_category(interaction.guild)
            except Exception as e:
                print(f"Errore durante la chiusura del ticket: {e}")
                await interaction.followup.send("Si è verificato un errore durante la chiusura del ticket", ephemeral=True)

    class TicketSelect(Select):
        def __init__(self, cog):
            super().__init__(
                placeholder="Selezione un'opzione...",
                options=[
                    discord.SelectOption(label="🌍 Candidatura Evento", description="Candidati per prendere parte all'evento più imminente sul server"),
                    discord.SelectOption(label="📹 Candidatura Content Creator", description="Candidati per ottenere i privilegi da content creator"),
                    discord.SelectOption(label="🔧 Candidatura Staff", description="Candidati per entrare a far parte dello staff"),
                    discord.SelectOption(label="❓ Aiuto o info", description="Per aiuto o informazioni generali"),
                    discord.SelectOption(label="🎫 Segnalazione di uno o più utenti", description="Segnala uno o più utenti che non stanno rispettando il regolamento o bug abusando"),
                    discord.SelectOption(label="❕ Altro...", description="Per qualsiasi altra richiesta non elencata sopra")
                ]
            )
            self.cog = cog

        async def callback(self, interaction: discord.Interaction):
            try:
                guild = interaction.guild

                category_name = self.cog.category_map.get(self.values[0])
                if category_name:
                    category = discord.utils.get(guild.categories, name=category_name)
                    if category is None:
                        category = await guild.create_category(category_name)

                selected_option = self.values[0]
                channel_name = f"ticket-{interaction.user.name}".replace(" ", "-").lower()
                existing_channel = discord.utils.get(guild.channels, name=channel_name)
                staff_role = interaction.guild.get_role(self.cog.STAFF_ROLE_ID)
            
                if existing_channel:
                    await interaction.response.send_message(f"Hai già un ticket aperto: {existing_channel.mention}", ephemeral=True)
                    return

                ticket_channel = await guild.create_text_channel(
                    channel_name,
                    category=category,
                    topic=f"Ticket aperto da {interaction.user} per {selected_option}"
                )

                await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
                await ticket_channel.set_permissions(guild.default_role, read_messages=False)
                await ticket_channel.set_permissions(staff_role, read_messages=True, send_messages=True)
                await interaction.response.send_message(f"Ticket creato: {ticket_channel.mention}", ephemeral=True)
                
                embed_ticket = discord.Embed(
                    title=f":ticket: Ticket - {selected_option}",
                    description=f"**{interaction.user.mention} ha aperto un ticket per {selected_option}.**\n\nEsponi il tuo problema/richiesta in modo chiaro e dettagliato. Risponderemo al più presto possibile.",
                    color=discord.Color(0xff7900)
                )
                
                embed_ticket.set_footer(text="LegoChris Ticket System", icon_url=guild.icon.url)
                embed_ticket.set_thumbnail(url=guild.icon.url)
                view = Tickets.TicketActions(self.cog, ticket_channel, interaction.user)
                
                message = await ticket_channel.send(embed=embed_ticket, view=view)
                staffping = await ticket_channel.send(f"{staff_role.mention}")
                await staffping.delete()

                ticket_data = self.cog.load_ticket_data()
                ticket_id = self.cog.increment_ticket_id()
                ticket_data[channel_name] = {
                    "channel_id": ticket_channel.id,
                    "message_id": message.id,
                    "user_id": interaction.user.id,
                    "claimed_by": None,
                    "closed_by": None,
                    "id": ticket_id,
                    "created_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "closed_at": None,
                    "reason": None,
                    "button_data": {
                        "claim_button": False,
                        "close_with_reason_button": False
                    }
                }
                self.cog.save_ticket_data(ticket_data)

                self.view.clear_items()
                self.view.add_item(Tickets.TicketSelect(self.cog))
                await interaction.message.edit(view=self.view)
            except Exception as e:
                print(f"Errore durante la creazione del ticket: {e}")
                await interaction.response.send_message("Si è verificato un errore durante la creazione del ticket", ephemeral=True)

    class TicketView(View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog
            self.add_item(Tickets.TicketSelect(cog))
            
    class TicketActions(View):
        def __init__(self, cog, ticket_channel, user):
            super().__init__(timeout=None)
            self.cog = cog
            self.add_item(Tickets.ClaimButton(cog, ticket_channel, user))
            self.add_item(Tickets.CloseWithReasonButton(cog, ticket_channel, user))

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.bot.user} è online e pronto per l'uso!")

        data = self.load_data()
        if "message_id" in data and "channel_id" in data:
            channel = self.bot.get_channel(data["channel_id"])
            if channel:
                try:
                    message = await channel.fetch_message(data["message_id"])
                    view = Tickets.TicketView(self)
                    await message.edit(view=view)
                    print("Menu di selezione ripristinato con successo!")
                except discord.NotFound:
                    print("Il messaggio persistente non è stato trovato.")
            else:
                print("Il canale persistente non è stato trovato.")
                
        # Carica i dati dei ticket
        ticket_data = self.load_ticket_data()
        for ticket in ticket_data.values():
            channel = self.bot.get_channel(ticket["channel_id"])
            if channel:
                try:
                    user = await self.bot.fetch_user(ticket["user_id"])
                    view = Tickets.TicketActions(self, ticket_channel=channel, user=user)
                    messages = [message async for message in channel.history(limit=100)]
                    for message in messages:
                        if message.embeds and message.embeds[0].title.startswith(":ticket: Ticket -"):
                            await message.edit(view=view)
                            break
                    print(f"Ticket Actions ripristinato per il ticket dell'utente {user.name}!")
                except discord.NotFound:
                    print(f"Utente con ID {ticket['user_id']} non trovato per ticket {ticket['id']}")
                except Exception as e:
                    print(f"Errore nel ripristino del ticket {ticket['id']}: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True) 
    async def tsetup(self, ctx):
        guild = ctx.guild

        category = discord.utils.get(guild.categories, name=self.TICKET_CATEGORY_NAME)
        log_category = discord.utils.get(guild.categories, name=self.TICKET_CATEGORY_LOGS)
        if category is None:
            category = await guild.create_category(self.TICKET_CATEGORY_NAME)
        if log_category is None:
            log_category = await guild.create_category(self.TICKET_CATEGORY_LOGS)       
        ticket_channel = discord.utils.get(guild.channels, name=self.TICKET_CHANNEL_NAME, category=category)
        log_channel = discord.utils.get(guild.channels, name=self.TICKET_CHANNEL_LOGS, category=log_category)
        if ticket_channel is None:
            ticket_channel = await guild.create_text_channel(self.TICKET_CHANNEL_NAME, category=category)
        if log_channel is None:
            log_channel = await guild.create_text_channel(self.TICKET_CHANNEL_LOGS, category=log_category)

        embed = discord.Embed(
            title=":ticket: Ticket", 
            description="**Se hai bisogno di aiuto, apri un ticket selezionando una categoria dal menù a tendina qui sotto.**\n\n**Seleziona la categoria che meglio descrive il tuo problema/richiesta.**\n\n**Se non trovi la categoria adatta, seleziona 'Altro...'**\n\n - 🌍 **Candidatura Evento:** Candidati per prendere parte all'evento più imminente sul server\n\n - 📹 **Candidatura Content Creator:** Candidati per ottenere i privilegi da content creator\n\n - 🔧 **Candidatura Staff:** Candidati per entrare a far parte dello staff\n\n - ❓ **Aiuto o info:** Per aiuto o informazioni generali\n\n - 🎫 **Segnalazione di uno o più utenti:** Segnala uno o più utenti che non stanno rispettando il regolamento o bug abusando\n\n - ❕ **Altro...:** Per qualsiasi altra richiesta non elencata sopra",
            color=discord.Color(0xff7900)
        )
        embed.set_footer(text="LegoChris Ticket System", icon_url=ctx.guild.icon.url)
        embed.set_thumbnail(url=ctx.guild.icon.url)
        
        view = Tickets.TicketView(self)
        messages = [message async for message in ticket_channel.history(limit=100)]
        embed_sent = False
        for message in messages:
            if message.embeds and message.embeds[0].title == embed.title:
                embed_sent = True
                break

        if not embed_sent:
            message = await ticket_channel.send(file = discord.File("./data/tickets/Tickets_MT.png"), embed=embed, view=view)

            data = {
                "channel_id": ticket_channel.id,
                "message_id": message.id
            }
            self.save_data(data)
            
            await ctx.send("Il sistema di ticket è stato configurato con successo.")
        else:
            await ctx.send("Il sistema di ticket è già stato configurato.")

    @app_commands.command(name="tclaim", description="Claima un ticket del sistema di supporto")
    async def tclaim(self, interaction: discord.Interaction):
        """Slash command per claimare un ticket"""
        try:
            # Verifica che l'utente abbia il ruolo staff
            staff_role = interaction.guild.get_role(self.STAFF_ROLE_ID)
            if staff_role not in interaction.user.roles:
                await interaction.response.send_message("❌ Non hai i permessi per claimare i ticket", ephemeral=True)
                return

            # Verifica che il comando sia stato usato in un canale ticket
            ticket_data = self.load_ticket_data()
            ticket_info = None
            ticket_name = None
            
            for name, info in ticket_data.items():
                if info.get("channel_id") == interaction.channel.id:
                    ticket_info = info
                    ticket_name = name
                    break
            
            if not ticket_info:
                await interaction.response.send_message("❌ Questo comando può essere usato solo nei canali ticket", ephemeral=True)
                return

            # Verifica se il ticket è già stato claimato
            if ticket_info.get("claimed_by"):
                await interaction.response.send_message("❌ Questo ticket è già stato claimato", ephemeral=True)
                return

            # Ottieni l'utente che ha aperto il ticket
            user_id = ticket_info.get("user_id")
            try:
                user = await interaction.guild.fetch_member(user_id)
            except discord.NotFound:
                await interaction.response.send_message("⚠️ L'utente che ha aperto questo ticket non è più nel server", ephemeral=True)
                return

            # Imposta i permessi del canale
            await interaction.channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
            await interaction.channel.set_permissions(staff_role, read_messages=True, send_messages=False)

            # Aggiorna i dati del ticket
            ticket_info["claimed_by"] = interaction.user.mention
            self.save_ticket_data(ticket_data)

            # Rimuovi il pulsante Claim dal messaggio embed se presente
            try:
                messages = [message async for message in interaction.channel.history(limit=100)]
                for message in messages:
                    if message.embeds and message.embeds[0].title.startswith(":ticket: Ticket -"):
                        if message.components:
                            view = View.from_message(message)
                            # Rimuovi il pulsante claim
                            items_to_keep = []
                            for item in view.children:
                                if hasattr(item, 'custom_id') and item.custom_id != "claim":
                                    items_to_keep.append(item)
                            
                            new_view = View(timeout=None)
                            for item in items_to_keep:
                                new_view.add_item(item)
                            
                            await message.edit(view=new_view)
                        break
            except Exception as e:
                print(f"Errore durante la rimozione del pulsante claim: {e}")

            await interaction.response.send_message(f"✅ Ticket claimato da {interaction.user.mention}")
            
        except Exception as e:
            print(f"Errore durante il claim del ticket: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Si è verificato un errore durante il claim del ticket", ephemeral=True)
            else:
                await interaction.followup.send("❌ Si è verificato un errore durante il claim del ticket", ephemeral=True)

    @app_commands.command(name="tclose", description="Chiudi un ticket con un motivo")
    @app_commands.describe(motivo="Il motivo della chiusura del ticket")
    async def tclose(self, interaction: discord.Interaction, motivo: str = "Nessun motivo specificato"):
        """Slash command per chiudere un ticket con un motivo"""
        try:
            # Verifica che l'utente abbia il ruolo staff
            staff_role = interaction.guild.get_role(self.STAFF_ROLE_ID)
            if staff_role not in interaction.user.roles:
                await interaction.response.send_message("❌ Non hai i permessi per chiudere i ticket", ephemeral=True)
                return

            # Verifica che il comando sia stato usato in un canale ticket
            ticket_data = self.load_ticket_data()
            ticket_info = None
            ticket_name = None
            
            for name, info in ticket_data.items():
                if info.get("channel_id") == interaction.channel.id:
                    ticket_info = info
                    ticket_name = name
                    break
            
            if not ticket_info:
                await interaction.response.send_message("❌ Questo comando può essere usato solo nei canali ticket", ephemeral=True)
                return

            # Invia messaggio di conferma
            await interaction.response.send_message(f"🔒 Ticket chiuso con motivo: {motivo}")
            await asyncio.sleep(2)

            # Prepara i dati per il log
            log_channel = discord.utils.get(interaction.guild.channels, name=self.TICKET_CHANNEL_LOGS)
            if not log_channel:
                await interaction.followup.send("⚠️ Canale log non trovato", ephemeral=True)
                return

            ticket_id = ticket_info.get("id", self.get_current_ticket_id())
            created_at = ticket_info.get("created_at", "Unknown")
            claimed_by = ticket_info.get("claimed_by", "Not Claimed")
            closed_by = interaction.user.mention
            closed_at = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            user_id = ticket_info.get("user_id")

            # Ottieni l'utente che ha aperto il ticket
            try:
                user = await interaction.guild.fetch_member(user_id)
                opened_by = user.mention
            except discord.NotFound:
                opened_by = f"ID Utente: {user_id} (potrebbe aver lasciato il server)"

            # Aggiorna i dati del ticket
            ticket_info["closed_by"] = closed_by
            ticket_info["closed_at"] = closed_at
            ticket_info["reason"] = motivo
            self.save_ticket_data(ticket_data)

            # Crea l'embed per il log
            embed = discord.Embed(
                title=":ticket: Ticket Chiuso",
                color=discord.Color(0xff7900)
            )
            embed.add_field(name="Ticket ID", value=ticket_id, inline=True)
            embed.add_field(name="Aperto da", value=opened_by, inline=True)
            embed.add_field(name="Chiuso da", value=closed_by, inline=True)
            embed.add_field(name="Claimato da", value=claimed_by, inline=True)
            embed.add_field(name="Aperto il", value=created_at, inline=True)
            embed.add_field(name="Chiuso il", value=closed_at, inline=True)
            embed.add_field(name="Motivo", value=motivo, inline=False)
            embed.set_footer(text="LegoChris Ticket System", icon_url=interaction.guild.icon.url)
            embed.set_thumbnail(url=interaction.guild.icon.url)

            # Genera il transcript
            transcript_file = await self.generate_transcript(interaction.channel)
            
            # Invia il log con transcript allegato
            if transcript_file:
                await log_channel.send(embed=embed)
                with open(transcript_file, "rb") as file:
                    await log_channel.send(file=discord.File(file, filename=f"transcript_{interaction.channel.id}.txt"))
                # Pulisci il file dopo l'uso
                try:
                    os.remove(transcript_file)
                except Exception as e:
                    print(f"Errore durante la pulizia del file transcript: {e}")
            else:
                await log_channel.send(embed=embed)
                await log_channel.send("⚠️ Impossibile generare il transcript del ticket")

            # Elimina il canale del ticket
            await interaction.channel.delete()
            
            # Elimina le categorie vuote
            await self.delete_void_ticket_category(interaction.guild)
            
        except Exception as e:
            print(f"Errore durante la chiusura del ticket: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Si è verificato un errore durante la chiusura del ticket", ephemeral=True)
            else:
                await interaction.followup.send("❌ Si è verificato un errore durante la chiusura del ticket", ephemeral=True)

async def setup(bot):
    """Register the cog in the bot instance."""
    await bot.add_cog(Tickets(bot)) 