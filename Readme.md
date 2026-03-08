# 🚀 Rockets Tracker

A personal cycling tracker for **Unibet Rose Rockets** — a Dutch ProTeam chasing WorldTour promotion. Tracks UCI points, race results, and team ranking in a dark-themed web app backed by a local Python API.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green) ![SQLite](https://img.shields.io/badge/SQLite-local-lightgrey)

---

## What it does

| Tab | What you see |
|---|---|
| **UCI Standings** | Rider leaderboard with UCI + PCS points, click any rider for full season results |
| **Alerts** | Spoiler-free notifications when a Rockets rider scores points — reveal at your own pace |
| **Points Guide** | UCI points per position per race class, with notification thresholds |
| **Team Ranking** | Full WT + PRT ranking table with Rockets highlighted and trend arrows |

---

## Project structure

```
Rockets-App/
├── backend/
│   ├── config.py              # Team slugs, season, DB path
│   ├── app.py                 # Uvicorn entry point
│   ├── requirements.txt
│   ├── api/
│   │   └── main.py            # FastAPI endpoints
│   ├── db/
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   └── sync.py            # Scrape → SQLite orchestrator
│   ├── scraper/
│   │   ├── uci_ranking.py     # UCI team ranking scraper
│   │   └── ...
│   └── tests/
│       ├── test_sync.py       # Unit tests for sync helpers
│       ├── test_uci_ranking.py
│       └── test_api.py        # API integration tests
├── docs/
│   └── data_model.md
└── index.html                 # Web app — open directly in browser
```

---

## Setup

**Requirements:** Python 3.11+

```bash
# 1. Clone
git clone https://github.com/j-vanlieshout/Rockets-App.git
cd Rockets-App

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r backend/requirements.txt
```

---

## Running

### 1. Sync data from ProCyclingStats

```bash
cd backend
python db/sync.py              # current season
python db/sync.py --season 2025
```

This scrapes the Rockets roster, rider profiles, race results, and UCI points from PCS and saves everything to a local `pcs_tracker.db` SQLite file. Re-run anytime to pick up new results.

### 2. Start the API

```bash
cd backend
python -m uvicorn api.main:app
```

API runs at `http://127.0.0.1:8000`. Interactive docs at `/docs`.

> **Note:** Run without `--reload` on Windows due to a multiprocessing limitation.

### 3. Open the web app

Open `index.html` directly in your browser. No web server needed.

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/teams` | List all tracked teams |
| GET | `/teams/{slug}/riders` | Full roster |
| GET | `/teams/{slug}/uci-standings?season=` | UCI leaderboard |
| GET | `/riders/{slug}/results?season=` | Rider season results |
| GET | `/races?season=` | All races with results |
| GET | `/races/{id}/results` | Results for one race |
| GET | `/ranking/teams?season=` | Live UCI team ranking |

---

## Configuration

Edit `backend/config.py` to change the tracked team or add more:

```python
TRACKED_TEAMS = [
    {
        "name": "Unibet Rose Rockets",
        "slug": "unibet-rose-rockets",   # PCS URL slug
        "uci_code": "URR",
    },
    # Add another team:
    # {"name": "Team Visma", "slug": "team-visma-lease-a-bike", "uci_code": "TJV"},
]
```

---

## Tests

```bash
cd backend
pip install pytest httpx
pytest tests/ -v
```

---

## Data source

All data is scraped from [ProCyclingStats](https://www.procyclingstats.com) using the [`procyclingstats`](https://github.com/themm1/procyclingstats) Python library. The UCI team ranking is fetched live on every page load; rider results are cached locally in SQLite.

---

## Notes

- The SQLite database (`pcs_tracker.db`) is gitignored — run `sync.py` after cloning to populate it.
- Some riders have incomplete PCS profiles (the library throws an `IndexError`). These riders are saved with roster data only and no season results.
- CORS is set to `allow_origins=["*"]` so the HTML file can talk to the API when opened locally via `file://`.