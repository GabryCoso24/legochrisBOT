"""Voice soundboard with queueing, playback controls and listings."""

import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio


class Soundboard(commands.GroupCog):
    """Handles queued sound playback in Discord voice channels."""

    def __init__(self, bot):
        self.bot = bot
        self.soundboard_path = "./data/soundboard"
        self.hidden_sounds = ["Mark Whatsapp"]
        self.queue = asyncio.Queue()
        self.voice_client = None
        self.current_task = None
        super().__init__()

    async def player_loop(self):
        while True:
            sound_name = None
            interaction = None
            selected_channel = None
            
            try:
                # Wait for a sound with a timeout if connected
                if self.voice_client and self.voice_client.is_connected():
                    try:
                        # 60 seconds timeout
                        sound_name, interaction, selected_channel = await asyncio.wait_for(self.queue.get(), timeout=60.0)
                    except asyncio.TimeoutError:
                        # Timeout reached, disconnect
                        if self.voice_client and self.voice_client.is_connected():
                            await self.voice_client.disconnect()
                            self.voice_client = None
                        continue
                else:
                    # Not connected, wait indefinitely
                    sound_name, interaction, selected_channel = await self.queue.get()

                sound_file = os.path.join(self.soundboard_path, f"{sound_name}.mp3")

                if not self.voice_client or not self.voice_client.is_connected():
                    # Usa il canale specificato, o quello dell'utente
                    channel = selected_channel or (interaction.user.voice.channel if interaction.user.voice else None)
                    if channel is None:
                        try:
                            await interaction.followup.send("❌ Non sei in un canale vocale e non ne hai specificato uno.", ephemeral=True)
                        except:
                            print(f"❌ Could not send error message to user")
                        self.queue.task_done()
                        continue
                    self.voice_client = await channel.connect()

                # Define a callback to capture errors
                current_sound = sound_name
                def after_playing(error):
                    if error:
                        print(f"❌ Playback Error: {error}")
                    else:
                        print(f"✅ Finished playing: {current_sound}")

                try:
                    source = discord.FFmpegPCMAudio(
                        sound_file,
                        options='-vn -b:a 128k'
                    )
                    self.voice_client.play(source, after=after_playing)
                except Exception as e:
                    try:
                        await interaction.followup.send(f"❌ Errore critico audio (FFmpeg?): {str(e)}", ephemeral=True)
                    except:
                        print(f"FFmpeg/Audio Error: {e}")
                    self.queue.task_done()
                    continue

                embed = discord.Embed(
                    title="🎵 Riproduzione in corso",
                    description=f"Sto riproducendo: **{sound_name}**",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Richiesto da {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
                
                # Try to send, but handle if interaction is expired
                try:
                    await interaction.followup.send(embed=embed, ephemeral=False)
                except Exception as e:
                    print(f"Could not send playing message: {e}")

                while self.voice_client and self.voice_client.is_playing():
                    await asyncio.sleep(0.5)
                
                self.queue.task_done()
                
            except asyncio.CancelledError:
                print("Player loop cancelled")
                break
            except Exception as e:
                print(f"Error in player_loop: {e}")
                import traceback
                traceback.print_exc()
                if sound_name is not None:
                    self.queue.task_done()

    @app_commands.command(name="playsound", description="Riproduci un suono dalla soundboard")
    @app_commands.describe(
        sound_name="Nome del suono da riprodurre",
        channel="Canale vocale dove riprodurre il suono (opzionale)"
    )
    async def playsound(self, interaction: discord.Interaction, sound_name: str, channel: discord.VoiceChannel | None = None):
        await interaction.response.defer()

        sound_file = os.path.join(self.soundboard_path, f"{sound_name}.mp3")
        if not os.path.exists(sound_file):
            embed = discord.Embed(
                title="❌ Suono non trovato",
                description=f"Il suono '{sound_name}' non esiste!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        await self.queue.put((sound_name, interaction, channel))

        if self.current_task is None or self.current_task.done():
            self.current_task = asyncio.create_task(self.player_loop())

        await interaction.followup.send(f"✅ Suono **{sound_name}** aggiunto alla coda!", ephemeral=True)

    @app_commands.command(name="skip", description="Salta il suono attualmente in riproduzione")
    async def skip(self, interaction: discord.Interaction):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
            await interaction.response.send_message("⏭️ Suono saltato!")
        else:
            await interaction.response.send_message("❌ Nessun suono in riproduzione al momento.")

    @app_commands.command(name="stop", description="Ferma la riproduzione e svuota la coda")
    async def stop(self, interaction: discord.Interaction):
        if self.voice_client and self.voice_client.is_connected():
            self.voice_client.stop()
            await self.voice_client.disconnect()
            self.voice_client = None

        while not self.queue.empty():
            self.queue.get_nowait()
            self.queue.task_done()

        if self.current_task:
            self.current_task.cancel()
            self.current_task = None

        await interaction.response.send_message("🛑 Riproduzione fermata e coda svuotata.")

    @app_commands.command(name="queue", description="Mostra la coda dei suoni")
    async def show_queue(self, interaction: discord.Interaction):
        if self.queue.empty():
            await interaction.response.send_message("📭 La coda è vuota.")
            return

        items = list(self.queue._queue)
        queue_text = "\n".join([f"{i+1}. {item[0]}" for i, item in enumerate(items)])

        embed = discord.Embed(
            title="📜 Coda Attuale",
            description=queue_text,
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Totale in coda: {len(items)}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="listsounds", description="Elenca tutti i suoni disponibili")
    async def listsounds(self, interaction: discord.Interaction):
        try:
            sounds = [f[:-4] for f in os.listdir(self.soundboard_path) if f.endswith(".mp3") and f[:-4] not in self.hidden_sounds]
            if sounds:
                embed = discord.Embed(
                    title="🎵 Suoni Disponibili",
                    description="Ecco la lista dei suoni disponibili:",
                    color=discord.Color.blue()
                )
                chunks = [sounds[i:i + 15] for i in range(0, len(sounds), 15)]
                for i, chunk in enumerate(chunks):
                    embed.add_field(
                        name=f"Pagina {i+1}",
                        value="\n".join([f"• {sound}" for sound in chunk]),
                        inline=False
                    )
                embed.set_footer(text=f"Totale suoni: {len(sounds)}")
                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Nessun suono",
                    description="Non ci sono suoni disponibili nella soundboard.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Errore",
                description=f"Errore durante il listing dei suoni: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)


async def setup(bot):
    """Register the cog in the bot instance."""
    await bot.add_cog(Soundboard(bot))
