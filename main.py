import os
import requests
import datetime
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext


# Logging
logging.basicConfig(level=logging.INFO)

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

# --- Function to fetch upcoming matches ---
def get_upcoming_matches(days=3):
    today = datetime.datetime.now().date()
    matches = []
    for i in range(days):
        date_str = str(today + datetime.timedelta(days=i))
        url = f"{BASE_URL}/fixtures?date={date_str}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            fixtures = data["response"]
            matches.extend(fixtures)
    return matches

# --- Command Handlers ---
async def start(def startupdate: Update, context: CallbackContext):
    await update.message.reply_text("⚽ Hello! I’m your Soccer Analytics Bot!")

async def matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = get_upcoming_matches()
    if not matches:
        await update.message.reply_text("No matches found.")
        return

    text = ""
    for match in matches[:5]:  # Limit to first 5
        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]
        date = match["fixture"]["date"]
        text += f"{home} vs {away} on {date}\n"
    await update.message.reply_text(text)

# --- Run the bot ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("matches", matches))
    app.run_polling()
