"""AI assistant cog with memory, role gating and optional voice TTS responses."""

import discord
from discord.ext import commands
from discord import app_commands

import sqlite3
import requests
import json
import os
import re
import asyncio
import edge_tts
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env.
load_dotenv()

# ---------- CONFIG ----------

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"  # Common choices: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo

MAX_CONTEXT_MESSAGES = 20

DATA_DIR = "data/ai"
DB_PATH = os.path.join(DATA_DIR, "memory.db")
TTS_DIR = os.path.join(DATA_DIR, "tts")
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "it-IT-GiuseppeMultilingualNeural")

# ElevenLabs config (leave empty to use Edge-TTS fallback)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam default voice
# Popular voices examples:
# "21m00Tcm4TlvDq8ikWAM" = Rachel
# "pNInz6obpgDQGcFmaJgB" = Adam
# Or use the voice ID of your custom voices.

ALIAS_REGEX = r"^da ora chiama <@!?(\d+)>\s+(.+)$"
ALIAS_REGEX2 = r"^ora chiama <@!(\d+)>\s+(.+)$"
ALIAS_REGEX3 = r"^chiama <@!(\d+)>\s+(.+)$"

# Patterns for self-alias commands ("call me ...")
SELF_ALIAS_REGEX = r"^da ora chiamami\s+(.+)$"
SELF_ALIAS_REGEX2 = r"^ora chiamami\s+(.+)$"
SELF_ALIAS_REGEX3 = r"^chiamami\s+(.+)$"


class AIMemory(commands.Cog):
    """Implements conversational AI memory, settings and speech features."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(TTS_DIR, exist_ok=True)

        self.conn = sqlite3.connect(DB_PATH)
        self.cur = self.conn.cursor()
        self._init_db()

        self.context_memory = {}  # channel_id -> list[{role, content}]
        self.tts_enabled = {}  # guild_id -> bool (TTS attivo o meno)
        
        # Inizializza client OpenAI
        self.openai_client = None
        if OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
                print("✅ OpenAI API attivata!")
            except Exception as e:
                print(f"❌ Errore inizializzazione OpenAI: {e}")
                raise
        else:
            print("❌ OPENAI_API_KEY non trovata nel file .env!")
            raise ValueError("OPENAI_API_KEY è richiesta")
        
        # Inizializza client ElevenLabs se API key presente
        self.elevenlabs_client = None
        if ELEVENLABS_API_KEY:
            try:
                self.elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
                print("✅ ElevenLabs TTS attivato!")
            except Exception as e:
                print(f"⚠️ Errore inizializzazione ElevenLabs: {e}")
                print("   Verrà usato Edge-TTS come fallback.")

    # ---------- DB INIT ----------

    def _init_db(self):
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            user_id TEXT,
            guild_id TEXT,
            key TEXT,
            value TEXT,
            importance INTEGER,
            created_at TEXT
        )
        """)

        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            guild_id TEXT PRIMARY KEY,
            ai_channel_id TEXT,
            allowed_role_id TEXT
        )
        """)

        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS user_aliases (
            owner_user_id TEXT,
            target_user_id TEXT,
            guild_id TEXT,
            alias TEXT,
            created_at TEXT,
            PRIMARY KEY (owner_user_id, target_user_id, guild_id)
        )
        """)

        self.conn.commit()

    # ---------- SHORT-TERM MEMORY ----------

    def add_context(self, context_id, role, content):
        self.context_memory.setdefault(context_id, []).append({
            "role": role,
            "content": content
        })
        self.context_memory[context_id] = self.context_memory[context_id][-MAX_CONTEXT_MESSAGES:]

    def get_context(self, context_id):
        return self.context_memory.get(context_id, [])

    # ---------- LONG-TERM MEMORY ----------

    def save_memory(self, user_id, guild_id, key, value, importance):
        self.cur.execute("""
        INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            guild_id,
            key,
            value,
            importance,
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()

    def get_user_memories(self, user_id, guild_id, limit=5):
        self.cur.execute("""
        SELECT key, value FROM memories
        WHERE user_id = ? AND guild_id = ?
        ORDER BY importance DESC, created_at DESC
        LIMIT ?
        """, (user_id, guild_id, limit))
        return self.cur.fetchall()

    # ---------- ALIAS ----------

    def save_alias(self, owner_id, target_id, guild_id, alias):
        # Alias globale: rimuove alias precedenti per questo target nel server
        self.cur.execute("""
        DELETE FROM user_aliases
        WHERE target_user_id = ? AND guild_id = ?
        """, (target_id, guild_id))
        
        self.cur.execute("""
        INSERT INTO user_aliases
        VALUES (?, ?, ?, ?, ?)
        """, (
            owner_id,
            target_id,
            guild_id,
            alias,
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()

    def get_aliases(self, guild_id):
        self.cur.execute("""
        SELECT target_user_id, alias
        FROM user_aliases
        WHERE guild_id = ?
        """, (guild_id,))
        return self.cur.fetchall()

    # ---------- SETTINGS ----------

    def set_settings(self, guild_id, channel_id, role_id):
        self.cur.execute("""
        INSERT OR REPLACE INTO settings VALUES (?, ?, ?)
        """, (guild_id, channel_id, role_id))
        self.conn.commit()

    def get_settings(self, guild_id):
        self.cur.execute("""
        SELECT ai_channel_id, allowed_role_id
        FROM settings WHERE guild_id = ?
        """, (guild_id,))
        return self.cur.fetchone()

    # ---------- OPENAI ----------

    def call_openai(self, messages):
        """Chiama l'API di OpenAI per generare una risposta."""
        try:
            response = self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
                max_completion_tokens=500  # Usato al posto di max_tokens per i nuovi modelli
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ Errore chiamata OpenAI: {e}")
            return f"Mi dispiace, si è verificato un errore: {str(e)}"

    def extract_memories_ai(self, text):
        system = {
            "role": "system",
            "content": (
                "Estrai SOLO informazioni personali stabili e utili nel tempo. "
                "Rispondi SOLO in JSON.\n"
                "{ \"memories\": [ {\"key\": \"\", \"value\": \"\", \"importance\": 1-5} ] }"
            )
        }

        user = {"role": "user", "content": text}

        try:
            response = self.call_openai([system, user])
            data = json.loads(response)
            return [m for m in data.get("memories", []) if m["importance"] >= 3]
        except Exception:
            return []

    # ---------- TTS HELPER ----------

    async def play_tts(self, guild, text):
        """Genera e riproduce TTS nel canale vocale del guild."""
        if not guild.voice_client or not guild.voice_client.is_connected():
            return False
        
        # Rimuovi i tag Discord dal testo
        clean_text = re.sub(r'<@!?(\d+)>', '', text).strip()
        
        if not clean_text:
            return False
        
        # Genera file audio
        tts_file = os.path.join(TTS_DIR, f"tts_{guild.id}_{int(asyncio.get_event_loop().time() * 1000)}.mp3")
        
        try:
            # Prova prima con ElevenLabs
            if self.elevenlabs_client:
                try:
                    print(f"🎤 Generazione TTS con ElevenLabs Turbo...")
                    
                    # Genera audio con ElevenLabs TURBO (ultra veloce)
                    audio_generator = self.elevenlabs_client.text_to_speech.convert(
                        voice_id=ELEVENLABS_VOICE_ID,
                        text=clean_text,
                        model_id="eleven_turbo_v2_5",  # MODELLO PIÙ VELOCE! (invece di multilingual_v2)
                        voice_settings=VoiceSettings(
                            stability=0.4,  # Ridotto per velocità
                            similarity_boost=0.7,  # Ridotto per velocità
                            style=0.0,
                            use_speaker_boost=True
                        ),
                        optimize_streaming_latency=4  # Max ottimizzazione latency (0-4, 4 = più veloce)
                    )
                    
                    # Salva l'audio in modo più efficiente
                    with open(tts_file, 'wb') as f:
                        for chunk in audio_generator:
                            f.write(chunk)
                    
                    print(f"✅ Audio generato: {len(clean_text)} caratteri")
                    
                except Exception as e:
                    print(f"⚠️ Errore ElevenLabs: {e}")
                    print(f"   Fallback a Edge-TTS...")
                    # Fallback a Edge-TTS
                    communicate = edge_tts.Communicate(clean_text, EDGE_TTS_VOICE)
                    await communicate.save(tts_file)
            else:
                # Usa Edge-TTS se ElevenLabs non è configurato
                communicate = edge_tts.Communicate(clean_text, EDGE_TTS_VOICE)
                await communicate.save(tts_file)
            
            # Attendi che l'audio corrente finisca (se in riproduzione)
            while guild.voice_client.is_playing():
                await asyncio.sleep(0.1)
            
            # Riproduci il nuovo audio
            audio_source = discord.FFmpegPCMAudio(tts_file)
            guild.voice_client.play(audio_source)
            
            # Attendi la fine della riproduzione
            while guild.voice_client.is_playing():
                await asyncio.sleep(0.1)
            
            return True
        except Exception as e:
            print(f"❌ Errore TTS: {e}")
            return False
        finally:
            # Pulisci il file
            if os.path.exists(tts_file):
                try:
                    await asyncio.sleep(0.5)
                    os.remove(tts_file)
                except:
                    pass


    # ---------- SLASH COMMANDS ----------

    @app_commands.command(name="ai_setup", description="Imposta il ruolo abilitato per l'AI")
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_setup(self, interaction: discord.Interaction,
                       role: discord.Role):
        self.set_settings(
            str(interaction.guild.id),
            "0",  # Channel ID ignored
            str(role.id)
        )
        await interaction.response.send_message(
            f"✅ AI attiva per chi ha il ruolo {role.mention} (richiede menzione).",
            ephemeral=True
        )

    @app_commands.command(name="ai_memory", description="Mostra cosa l'AI ricorda di te")
    async def ai_memory(self, interaction: discord.Interaction):
        memories = self.get_user_memories(
            str(interaction.user.id),
            str(interaction.guild.id)
        )
        if not memories:
            await interaction.response.send_message(
                "Non ricordo nulla di rilevante.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "\n".join(f"- **{k}**: {v}" for k, v in memories),
            ephemeral=True
        )

    @app_commands.command(name="ai_forget_me", description="Cancella tutta la memoria su di te")
    async def ai_forget_me(self, interaction: discord.Interaction):
        self.cur.execute("""
        DELETE FROM memories WHERE user_id = ? AND guild_id = ?
        """, (str(interaction.user.id), str(interaction.guild.id)))
        self.conn.commit()

        await interaction.response.send_message("🧠 Memoria cancellata.", ephemeral=True)

    @app_commands.command(name="join_ai", description="Il bot entra in vocale e risponde con TTS")
    async def join_ai(self, interaction: discord.Interaction):
        """Fa entrare il bot nel canale vocale con TTS automatico."""
        
        # Verifica se l'utente è in un canale vocale
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ Devi essere in un canale vocale!",
                ephemeral=True
            )
            return

        # Verifica ruolo
        settings = self.get_settings(str(interaction.guild.id))
        if settings:
            _, allowed_role_id = settings
            if not any(str(r.id) == allowed_role_id for r in interaction.user.roles):
                await interaction.response.send_message(
                    "❌ Non hai i permessi per usare l'AI!",
                    ephemeral=True
                )
                return

        voice_channel = interaction.user.voice.channel
        
        # Disconnetti se già connesso altrove
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
        
        try:
            await voice_channel.connect()
            self.tts_enabled[str(interaction.guild.id)] = True
            
            await interaction.response.send_message(
                f"🔊 Bot connesso a **{voice_channel.name}**! Ora risponderò anche con TTS quando mi pinghi.",
                ephemeral=False
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Errore: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="leave_ai", description="Il bot esce dal canale vocale")
    async def leave_ai(self, interaction: discord.Interaction):
        """Fa uscire il bot dal canale vocale."""
        
        if not interaction.guild.voice_client:
            await interaction.response.send_message(
                "❌ Non sono connesso a nessun canale vocale!",
                ephemeral=True
            )
            return
        
        await interaction.guild.voice_client.disconnect()
        self.tts_enabled[str(interaction.guild.id)] = False
        
        await interaction.response.send_message(
            "👋 Disconnesso dal canale vocale.",
            ephemeral=False
        )


    @app_commands.command(name="ai_speak", description="Fai parlare l'AI nel canale vocale")
    async def ai_speak(self, interaction: discord.Interaction, messaggio: str):
        """Fa parlare l'AI nel canale vocale dell'utente."""
        
        # Verifica se l'utente è in un canale vocale
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ Devi essere in un canale vocale!",
                ephemeral=True
            )
            return

        # Verifica ruolo
        settings = self.get_settings(str(interaction.guild.id))
        if settings:
            _, allowed_role_id = settings
            if not any(str(r.id) == allowed_role_id for r in interaction.user.roles):
                await interaction.response.send_message(
                    "❌ Non hai i permessi per usare l'AI!",
                    ephemeral=True
                )
                return

        await interaction.response.defer()

        # Ottieni il contesto dell'AI
        memories = self.get_user_memories(
            str(interaction.user.id),
            str(interaction.guild.id)
        )
        aliases = self.get_aliases(str(interaction.guild.id))
        unique_aliases = dict(aliases)

        memory_text = "\n".join(f"{k}: {v}" for k, v in memories) or "Nessuna."
        alias_text = (
            "\n".join(f"<@{uid}> si chiama '{a}'" for uid, a in unique_aliases.items())
            if unique_aliases else "Nessun soprannome."
        )

        prompt = [
            {"role": "system", "content": f"Sei un assistente Discord. Il tuo nome è LegoChrisBot. Rispondi SEMPRE in ITALIANO. L'utente che ti sta parlando è <@{interaction.user.id}>. Quando ti riferisci a lui, usa <@{interaction.user.id}>. Per altri utenti usa <@ID_UTENTE>. Non scrivere mai 'ID' letteralmente."},
            {"role": "system", "content": f"Memorie utente:\n{memory_text}"},
            {"role": "system", "content": f"Soprannomi:\n{alias_text}"},
            *self.get_context(str(interaction.guild.id)),
            {"role": "user", "content": messaggio}
        ]

        # Genera risposta
        response = self.call_openai(prompt)
        
        # Aggiungi al contesto
        self.add_context(str(interaction.guild.id), "user", messaggio)
        self.add_context(str(interaction.guild.id), "assistant", response)

        # Rimuovi i tag Discord dalla risposta per il TTS
        clean_response = re.sub(r'<@!?(\d+)>', '', response)
        
        # Genera file audio TTS
        tts_file = os.path.join(TTS_DIR, f"{interaction.id}.mp3")
        communicate = edge_tts.Communicate(clean_response, EDGE_TTS_VOICE)
        await communicate.save(tts_file)

        # Connetti al canale vocale
        voice_channel = interaction.user.voice.channel
        voice_client = None
        
        # Disconnetti se già connesso altrove
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
        
        try:
            voice_client = await voice_channel.connect()
            
            # Riproduci l'audio
            audio_source = discord.FFmpegPCMAudio(tts_file)
            voice_client.play(audio_source)
            
            await interaction.followup.send(f"🔊 **Risposta**: {response}")
            
            # Aspetta la fine della riproduzione
            while voice_client.is_playing():
                await asyncio.sleep(0.5)
            
            # Disconnetti dopo la riproduzione
            await voice_client.disconnect()
            
        except Exception as e:
            await interaction.followup.send(f"❌ Errore: {str(e)}")
            if voice_client and voice_client.is_connected():
                await voice_client.disconnect()
        
        finally:
            # Pulisci il file temporaneo
            if os.path.exists(tts_file):
                try:
                    os.remove(tts_file)
                except:
                    pass


    # ---------- MESSAGE HANDLER ----------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Verifica se il bot è menzionato nel messaggio
        if not self.bot.user in message.mentions:
            return

        settings = self.get_settings(str(message.guild.id))
        if not settings:
            return

        _, allowed_role_id = settings

        if not any(str(r.id) == allowed_role_id for r in message.author.roles):
            return

        # --- ALIAS PARSING ---
        # Puliamo il contenuto rimuovendo la menzione al bot per far funzionare i regex con ^
        content_cleaned = message.content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()
        
        match = re.search(ALIAS_REGEX, content_cleaned.lower()) or \
                re.search(ALIAS_REGEX2, content_cleaned.lower()) or \
                re.search(ALIAS_REGEX3, content_cleaned.lower())
        
        if match:
            target_id, alias = match.groups()
            self.save_alias(
                str(message.author.id),
                target_id,
                str(message.guild.id),
                alias
            )
            await message.channel.send(
                f"👌 Ok. Da ora <@{target_id}> è **{alias}**."
            )
            return
        
        # Controlla pattern auto-alias (chiamami)
        self_match = re.search(SELF_ALIAS_REGEX, content_cleaned.lower()) or \
                     re.search(SELF_ALIAS_REGEX2, content_cleaned.lower()) or \
                     re.search(SELF_ALIAS_REGEX3, content_cleaned.lower())
        
        if self_match:
            alias = self_match.group(1)
            self.save_alias(
                str(message.author.id),
                str(message.author.id),  # Auto-alias: target è l'autore stesso
                str(message.guild.id),
                alias
            )
            await message.channel.send(
                f"👌 Ok. Da ora ti chiamerò **{alias}**."
            )
            return

        # --- CONTEXT ---
        self.add_context(str(message.guild.id), "user", content_cleaned)

        memories = self.get_user_memories(
            str(message.author.id),
            str(message.guild.id)
        )
        aliases = self.get_aliases(str(message.guild.id))

        # Deduplica per target_user_id (converte in dict, mantenendo l'ultimo valore)
        unique_aliases = dict(aliases)

        memory_text = "\n".join(f"{k}: {v}" for k, v in memories) or "Nessuna."
        alias_text = (
            "\n".join(f"<@{uid}> si chiama '{a}'" for uid, a in unique_aliases.items())
            if unique_aliases else "Nessun soprannome."
        )

        prompt = [
            {"role": "system", "content": f"Sei un assistente Discord. Il tuo nome è LegoChrisBot. Rispondi SEMPRE in ITALIANO. L'utente che ti sta parlando è <@{message.author.id}>. Quando ti riferisci a lui, usa <@{message.author.id}>. Per altri utenti usa <@ID_UTENTE>. Non scrivere mai 'ID' letteralmente."},
            {"role": "system", "content": f"Memorie utente:\n{memory_text}"},
            {"role": "system", "content": f"Soprannomi:\n{alias_text}"},
            *self.get_context(str(message.guild.id)),
            {"role": "user", "content": content_cleaned}
        ]

        response = self.call_openai(prompt)

        self.add_context(str(message.guild.id), "assistant", response)

        extracted = self.extract_memories_ai(content_cleaned)
        for m in extracted:
            self.save_memory(
                str(message.author.id),
                str(message.guild.id),
                m["key"],
                m["value"],
                m["importance"]
            )

        # Invia messaggio in chat e prepara TTS in parallelo
        if self.tts_enabled.get(str(message.guild.id), False):
            # Avvia generazione TTS in background (non aspettiamo la fine)
            asyncio.create_task(self.play_tts(message.guild, response))
        
        await message.channel.send(response)


async def setup(bot: commands.Bot):
    await bot.add_cog(AIMemory(bot))
