import os
import requests
import datetime
import time
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Load from environment ---
API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# --- Util Function ---
def get_upcoming_fixtures(days=3):
    today = datetime.datetime.now().date()
    upcoming_matches = []

    for i in range(days):
        date_str = str(today + datetime.timedelta(days=i))
        print(f"Fetching fixtures for {date_str}...")
        url = f"{BASE_URL}/fixtures?date={date_str}"
        response = requests.get(url, headers=HEADERS)

        if response.status_code == 200:
            data = response.json()
            matches = data.get("response", [])
            for match in matches:
                teams = match["teams"]
                home = teams["home"]["name"]
                away = teams["away"]["name"]
                upcoming_matches.append(f"{home} vs {away} on {date_str}")
        else:
            print(f"Failed to fetch for {date_str}")

    return upcoming_matches

# --- /start Command Handler ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Hello! Your chat ID is: {chat_id}")

# --- /matches Command Handler ---
async def matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scanning upcoming matches...")
    fixtures = get_upcoming_fixtures()
    if fixtures:
        reply = "\n".join(fixtures)
    else:
        reply = "No strong matches found based on current criteria."
    await update.message.reply_text(reply)

# --- Main Bot Application ---
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("matches", matches))

    print("Bot started.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
