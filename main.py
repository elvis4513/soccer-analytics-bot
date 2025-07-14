# soccer_analytics_bot.py

import requests
import datetime
import time

API_KEY = "00b8f21845d964962927ca58d8bf5b34"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

# --- Utilities ---
def get_upcoming_fixtures(days=3):
    today = datetime.datetime.now().date()
    upcoming_matches = []
    for i in range(days):
        date_str = str(today + datetime.timedelta(days=i))
        print(f"Fetching fixtures for {date_str}...")
        url = f"{BASE_URL}/fixtures?date={date_str}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json().get("response", [])
            upcoming_matches.extend(data)
        else:
            print(f"Error: {response.status_code} - {response.text}")
        time.sleep(1)  # Respect API rate limits
    return upcoming_matches

def get_team_stats(team_id, league_id, season):
    url = f"{BASE_URL}/teams/statistics?team={team_id}&league={league_id}&season={season}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("response", {})
    else:
        print(f"Stats Error: {response.status_code} - {response.text}")
        return {}

def analyze_match(match):
    fixture = match["fixture"]
    league = match["league"]
    teams = match["teams"]

    season = league.get("season")
    league_id = league.get("id")
    home_id = teams["home"]["id"]
    away_id = teams["away"]["id"]

    home_stats = get_team_stats(home_id, league_id, season)
    away_stats = get_team_stats(away_id, league_id, season)

    # Safeguards
    if not home_stats or not away_stats:
        return None

    # --- Scoring Logic ---
    def goal_rate(stats):
        gf = stats.get("goals", {}).get("for", {}).get("average", {}).get("total", 0)
        ga = stats.get("goals", {}).get("against", {}).get("average", {}).get("total", 0)
        return float(gf or 0), float(ga or 0)

    def corners_avg(stats):
        return float(stats.get("corners", {}).get("total", {}).get("total", 0) or 0)

    home_gf, home_ga = goal_rate(home_stats)
    away_gf, away_ga = goal_rate(away_stats)

    home_corners = corners_avg(home_stats)
    away_corners = corners_avg(away_stats)

    avg_goals = (home_gf + away_ga + away_gf + home_ga) / 2
    avg_corners = (home_corners + away_corners) / 2

    # Simple confidence scores
    btts_conf = 1 if (home_gf > 1.0 and away_gf > 1.0) else 0
    o25_conf = 1 if avg_goals >= 2.8 else 0
    corners_conf = 1 if avg_corners >= 9.0 else 0

    return {
        "match": f"{teams['home']['name']} vs {teams['away']['name']}",
        "date": fixture.get("date"),
        "BTTS": btts_conf,
        "Over2.5": o25_conf,
        "Corners9+": corners_conf
    }

def run():
    print("\nScanning upcoming matches...\n")
    matches = get_upcoming_fixtures()
    results = []
    for match in matches:
        res = analyze_match(match)
        if res and (res['BTTS'] + res['Over2.5'] + res['Corners9+']) >= 2:
            results.append(res)
            print(res)

    if not results:
        print("No strong matches found based on current criteria.")

if __name__ == "__main__":
    run()
