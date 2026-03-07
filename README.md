# 🚴 PCS Team Tracker

A personal Android app + Python backend to track pro cycling teams using data scraped from [ProCyclingStats](https://www.procyclingstats.com).

Currently tracking: **Unibet Rose Rockets (URR)**

---

## Project Structure

```
pcs-tracker/
├── backend/                  # Python FastAPI scraper + REST API
│   ├── scraper/
│   │   ├── pcs_scraper.py    # Core HTTP + HTML parsing logic
│   │   ├── teams.py          # Team roster scraping
│   │   └── riders.py         # Individual rider profile scraping
│   ├── api/
│   │   └── main.py           # FastAPI REST endpoints
│   ├── db/
│   │   └── models.py         # SQLAlchemy ORM models (SQLite)
│   ├── config.py             # Team slugs, seasons, settings
│   └── requirements.txt
│
├── android/                  # Kotlin + Jetpack Compose app (coming soon)
│
└── docs/
    └── data-model.md         # Entity & field documentation
```

---

## Backend Setup

### Requirements
- Python 3.10+
- See `backend/requirements.txt`

### Install & run

```bash
cd backend
pip install -r requirements.txt

# Scrape the team roster once
python -m scraper.teams

# Start the API server
uvicorn api.main:app --reload
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/teams` | List all tracked teams |
| GET | `/teams/{slug}/riders` | Roster for a team |
| GET | `/riders/{slug}` | Full rider profile |
| GET | `/teams/{slug}/results` | Recent race results |

---

## Adding More Teams

Edit `backend/config.py` and add a new entry to `TRACKED_TEAMS`:

```python
TRACKED_TEAMS = [
    {"name": "Unibet Rose Rockets", "slug": "unibet-rose-rockets", "uci_code": "URR"},
    # {"name": "Another Team", "slug": "another-team-pcs-slug", "uci_code": "XYZ"},
]
```

The scraper will automatically pick up new teams on the next run.

---

## Data Sources

All data is scraped from [ProCyclingStats.com](https://www.procyclingstats.com). This is a personal project — please respect PCS's servers and don't run scrapers excessively.

---

## Roadmap

- [x] Backend scraper — team roster
- [ ] Backend scraper — race results
- [ ] Backend scraper — season standings
- [ ] FastAPI REST layer
- [ ] SQLite persistence
- [ ] Android app — rider list screen
- [ ] Android app — race results screen
- [ ] Android app — standings screen
