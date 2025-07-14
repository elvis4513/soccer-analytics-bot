import os
import asyncio
import logging
import requests
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from fastapi import FastAPI
import uvicorn

# --- Setup logging ---
logging.basicConfig(level=logging.INFO)

# --- Load environment variables ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# --- Telegram Bot Setup ---
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"✅ Your chat ID is: {chat_id}")
    logging.info(f"User started bot. Chat ID = {chat_id}")

application.add_handler(CommandHandler("start", start))

# --- Match Scanner ---
def get_upcoming_fixtures(days=3):
    today = datetime.datetime.now().date()
    upcoming_matches = []

    for i in range(days):
        date_str = str(today + datetime.timedelta(days=i))
        logging.info(f"📅 Fetching fixtures for {date_str}...")
        url = f"{BASE_URL}/fixtures?date={date_str}"

        try:
            res = requests.get(url, headers=HEADERS)
            data = res.json()
            matches = data.get("response", [])
            upcoming_matches.extend(matches)
        except Exception as e:
            logging.error(f"❌ Error fetching fixtures for {date_str}: {e}")

    return upcoming_matches

async def scan_matches():
    matches = get_upcoming_fixtures()
    logging.info(f"✅ Found {len(matches)} upcoming matches.")

    if TELEGRAM_CHAT_ID:
        if matches:
            send_telegram_message(f"📊 Found {len(matches)} matches to analyze.")
        else:
            send_telegram_message("⚠️ No strong matches found based on current criteria.")
    else:
        logging.warning("TELEGRAM_CHAT_ID not set yet.")

def send_telegram_message(message):
    if not TELEGRAM_CHAT_ID:
        logging.warning("TELEGRAM_CHAT_ID missing.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        logging.error(f"❌ Failed to send Telegram message: {e}")

# --- Async startup ---
async def main():
    await application.start()
    await application.updater.start_polling()
    await scan_matches()

# --- Keep Render alive with FastAPI ---
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Soccer Analytics Bot is alive"}

if __name__ == "__main__":
    asyncio.run(main())
    uvicorn.run(app, host="0.0.0.0", port=10000)
