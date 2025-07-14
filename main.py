import os
import requests
import datetime
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, JobQueue

# Logging
logging.basicConfig(level=logging.INFO)

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# --- Health check server for Render ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Soccer bot is running')

def run_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_server).start()

# --- Fetch upcoming matches with stats ---
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
            for match in fixtures:
                match_id = match["fixture"]["id"]

                # Predictions
                stats_url = f"{BASE_URL}/predictions?fixture={match_id}"
                stats_response = requests.get(stats_url, headers=HEADERS)
                if stats_response.status_code == 200:
                    match["stats"] = stats_response.json()["response"]

                # Corner stats
                corner_url = f"{BASE_URL}/fixtures/statistics?fixture={match_id}"
                corner_response = requests.get(corner_url, headers=HEADERS)
                if corner_response.status_code == 200:
                    match["corners"] = corner_response.json()["response"]

                matches.append(match)
    return matches

# --- Filter Logic ---
def filter_matches(matches, btts_threshold=80, over25_label="Over 2.5"):
    filtered = []
    for match in matches:
        try:
            pred = match.get("stats", [{}])[0].get("predictions", {})
            btts = int(pred.get("both_teams_to_score", {}).get("percentage", 0))
            over_label = pred.get("under_over", {}).get("label", "")
            if btts >= btts_threshold and over_label == over25_label:
                filtered.append(match)
        except:
            continue
    return filtered

# --- Display matches ---
def send_match_list(update: Update, matches):
    for match in matches[:29]:
        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]
        date = match["fixture"]["date"][:16].replace("T", " ")
        msg = f"\n📅 {date}: {home} vs {away}"

        if "stats" in match and match["stats"]:
            pred = match["stats"][0].get("predictions", {})
            if pred:
                winner = pred.get("winner", {}).get("comment", "N/A")
                win_or_draw = pred.get("win_or_draw", "N/A")
                under = pred.get("under_over", {}).get("label", "N/A")
                goals_avg = pred.get("goals", {}).get("total", "N/A")
                btts = pred.get("both_teams_to_score", {}).get("percentage", "N/A")

                msg += (
                    f"\n🏆 Tip: {winner}"
                    f"\n🔹 Win/Draw: {win_or_draw}"
                    f"\n⚽ Avg Goals: {goals_avg}"
                    f"\n📊 Over/Under: {under}"
                    f"\n🤝 BTTS Chance: {btts}%"
                )

        if "corners" in match and match["corners"]:
            total_corners = 0
            for team_stats in match["corners"]:
                for stat in team_stats.get("statistics", []):
                    if stat["type"].lower() == "corners":
                        total_corners += stat.get("value", 0) or 0
            msg += f"\n🟡 Total Corners: {total_corners}"

        update.message.reply_text(msg)

# --- Start Command ---
def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("All Matches", callback_data='all')],
        [InlineKeyboardButton("Filtered Matches", callback_data='filtered')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("⚽ Hello! I’m your Soccer Analytics Bot!\nChoose an option:", reply_markup=reply_markup)

# --- Inline Button Logic ---
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    matches = get_upcoming_matches()

    if query.data == 'all':
        query.edit_message_text("📋 Showing all matches...")
        send_match_list(query, matches)
    elif query.data == 'filtered':
        filtered = filter_matches(matches)
        if filtered:
            query.edit_message_text("✅ High-confidence matches...")
            send_match_list(query, filtered)
        else:
            query.edit_message_text("⚠️ No matches meet the filter criteria.")

# --- Daily Auto Alerts ---
def daily_alert(context: CallbackContext):
    bot = context.bot
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    matches = get_upcoming_matches()
    if matches:
        for match in matches[:10]:
            home = match["teams"]["home"]["name"]
            away = match["teams"]["away"]["name"]
            date = match["fixture"]["date"][:16].replace("T", " ")
            text = f"📅 {date}: {home} vs {away}"
            bot.send_message(chat_id=chat_id, text=text)

# --- Launch bot ---
if __name__ == "__main__":
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))

    # Auto send matches every day at 8:00 AM UTC
    updater.job_queue.run_daily(daily_alert, time=datetime.time(hour=8, minute=0))

    updater.start_polling()
    updater.idle()
