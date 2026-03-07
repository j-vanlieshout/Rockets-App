# config.py
# Central place to manage tracked teams and scraper settings.
# To follow a new team, just add an entry to TRACKED_TEAMS.

import datetime

# ── Teams ──────────────────────────────────────────────────────────────────────

TRACKED_TEAMS = [
    {
        "name": "Unibet Rose Rockets",
        "slug": "unibet-rose-rockets",   # PCS slug prefix (year is appended automatically)
        "uci_code": "URR",
    },
    # Add more teams here, e.g.:
    # {"name": "Team Visma", "slug": "team-visma-lease-a-bike", "uci_code": "TJV"},
]

# ── Season ─────────────────────────────────────────────────────────────────────

CURRENT_SEASON = datetime.date.today().year  # e.g. 2026

# ── Scraper settings ───────────────────────────────────────────────────────────

PCS_BASE_URL = "https://www.procyclingstats.com"

# Mimic a real browser to avoid 403 blocks
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Seconds to wait between requests — be polite to PCS
SCRAPE_DELAY_SECONDS = 2.0

# ── Database ───────────────────────────────────────────────────────────────────

DATABASE_URL = "sqlite:///./pcs_tracker.db"
