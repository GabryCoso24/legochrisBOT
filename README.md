# legochrisBOT

A modular Discord bot built with Python and `discord.py`, featuring moderation, tickets, reaction roles, AI/TTS, soundboard, and community utilities.

## Features

- Automatic cog loading from `cogs/`
- Slash command support (`/` commands)
- Ticket system with claim/close flow and transcript logs
- Rule management with JSON persistence and embed publishing
- Persistent reaction roles
- Moderation tools (ban/unban, temporary bans, role management)
- AI memory and voice features (OpenAI + TTS)
- Voice soundboard with playback queue

## Requirements

- Python 3.10+
- `ffmpeg` available in PATH (required for voice/audio features)
- A Discord bot application configured in the Discord Developer Portal

## Installation

```bash
git clone https://github.com/GabryCoso24/legochrisBOT.git
cd legochrisBOT
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Environment Configuration

Create a `.env` file in the project root.
You can start by copying `.env.example`.

Example:

```env
TOKEN=your_discord_bot_token
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
EDGE_TTS_VOICE=it-IT-GiuseppeMultilingualNeural
```

### Environment variables

- `TOKEN` (required): Discord bot token
- `OPENAI_API_KEY` (required by AI cog): OpenAI API key
- `ELEVENLABS_API_KEY` (optional): enables ElevenLabs TTS; if missing, Edge-TTS fallback is used
- `EDGE_TTS_VOICE` (optional): Edge-TTS voice name used for fallback and direct TTS output

## Running the Bot

### Direct

```bash
python3 bot.py
```

### Via script

```bash
bash start.sh
```

> `start.sh` contains a placeholder path (`/home/YOURUSERNAME/legochrisbot`). Update it to your real local path before using it.

## Project Structure

```text
bot.py
requirements.txt
start.sh
cogs/
data/
media/
```

- `bot.py`: bot entrypoint, intents setup, slash sync, dynamic cog loading
- `cogs/`: feature modules
- `data/`: persistent data (JSON/SQLite, logs, transcripts)
- `media/`: static media used by commands

## Main Cogs

- `ai.py`: AI memory, role-gated behavior, TTS, and AI slash commands
- `ban.py`: ban/unban moderation
- `fun.py`: games and entertainment commands
- `id.py`: quick user ID command
- `legacy.py`: legacy text commands
- `messages.py`: predefined embeds
- `nsfw.py`: NSFW media command
- `reactionroles.py`: reaction role mapping and listeners
- `roles.py`: role add/remove (single and bulk)
- `rules.py`: create/edit/remove/publish rule lists
- `salvini.py`: random themed media command
- `soundboard.py`: queued voice sound playback
- `talent.py`: talent registration and leaderboard
- `tempban.py`: temp-ban scheduling and management
- `tickets.py`: ticket panel, category routing, claim, close, transcripts
- `userinfo.py`: extended user profile information

## Key Slash Commands (examples)

- Rules: `/add_rule`, `/add_rules`, `/remove_rule`, `/edit_rule`, `/edit_rules`, `/create_rules`, `/send_rules`
- Moderation: `/ban`, `/unban`, `/tempban`, `/tempban_modify`, `/tempban_remove`, `/listtempbans`, `/addrole`, `/removerole`
- Tickets: `/tclaim`, `/tclose`
- AI: `/ai_setup`, `/ai_memory`, `/ai_forget_me`, `/join_ai`, `/leave_ai`, `/ai_speak`
- Utility: `/userinfo`, `/id`, `/message`, `/setreactionrole`, `/removereactionrole`, `/playsound`, `/queue`, `/skip`, `/stop`, `/listsounds`

## Recommended Discord Permissions

Depending on enabled cogs, grant the bot permissions such as:

- `Manage Roles`
- `Ban Members`
- `Manage Channels`
- `Send Messages`
- `Read Message History`
- `Attach Files`
- `Use Application Commands`
- `Connect` / `Speak`

## Data Persistence

Runtime data is stored in `data/`, including:

- JSON: rules, reaction roles, tickets, tempbans, talent data
- SQLite: AI memory (`data/ai/memory.db`)
- Ticket transcripts: `data/tickets/logs/`

For backup/migration, copy the `data/` directory.

## Troubleshooting

- Bot does not start: verify `.env` values and active virtual environment
- Slash commands do not appear: check OAuth scopes/permissions and sync timing
- Voice/audio fails: verify `ffmpeg` installation and bot voice permissions
- AI errors: verify `OPENAI_API_KEY`
- ElevenLabs TTS not working: verify `ELEVENLABS_API_KEY`

## Security Notes

- Never commit real tokens or API keys.
- Rotate keys immediately if exposed.
- Keep sensitive values only in environment variables or a secure secret manager.

## License

This project uses a custom restrictive license. See `LICENSE` for details.
In short: copying/republishing the project is not permitted, but limited use as a reference for learning is allowed.
