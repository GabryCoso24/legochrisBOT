#!/bin/bash
# start.sh - avvia il bot Discord con venv

# Vai nella cartella del bot
cd /home/YOURUSERNAME/legochrisbot || exit 1

# Attiva il venv
source venv/bin/activate

# Avvia il bot
python3 bot.py
