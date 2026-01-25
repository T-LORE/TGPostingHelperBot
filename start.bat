@echo off
title Smart Telegram Poster Bot
echo ===============================================
echo ==  Smart Telegram Auto-Poster Bot Launcher  ==
echo ===============================================

if not exist ".venv" (
    echo [+] Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate

echo [+] Installing dependencies...
pip install -r requirements.txt

echo ===============================================
echo Starting the bot...
echo To stop the bot, press Ctrl+C in this window.
echo ===============================================
python run.py

pause