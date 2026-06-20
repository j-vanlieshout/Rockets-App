# 🚀 Rockets Tracker

A personal cycling tracker for **Unibet Rose Rockets** — a Dutch ProTeam chasing WorldTour promotion. Tracks UCI points, race results, and team ranking in a dark-themed web app backed by a local Python API.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![SQLite](https://img.shields.io/badge/SQLite-local-lightgrey) ![GitHub Pages](https://img.shields.io/badge/hosting-GitHub%20Pages-green)

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
│   ├── requirements.txt
│   ├── build/
│   │   ├── export.py          # DB → docs/data/*.json
│   │   ├── alerts.py          # Ping ladder, dedup, ntfy edge
│   │   └── run.py             # Build orchestrator
│   ├── db/
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   └── sync.py            # Scrape → SQLite orchestrator
│   ├── scraper/
│   │   ├── uci_ranking.py     # UCI team ranking scraper
│   │   └── ...
│   └── tests/
│       ├── test_sync.py       # Unit tests for sync helpers
│       ├── test_uci_ranking.py
│       ├── test_export.py     # JSON export tests
│       └── test_alerts.py     # Ping ladder + dedup tests
├── docs/
│   ├── index.html             # Web app — static, reads ./data/*.json
│   └── data/                  # Exported JSON (published by the scheduled scrape)
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

### 2. Export the static JSON

```bash
cd backend
python -m build.run
```

This reads `pcs_tracker.db`, writes `docs/data/*.json` (standings, ranking,
results, meta), and — if `NTFY_TOPIC` is set — sends spoiler-free pings for any
newly notable results. There is **no server**.

### 3. Open the web app

Open `docs/index.html` in your browser. It reads `./data/*.json` from the same
folder. In production a scheduled GitHub Action runs steps 1–2 and commits the
JSON, and GitHub Pages serves `docs/`.

---

## Data files

The frontend reads these static files from `docs/data/` (no API):

| File | Contents |
|---|---|
| `standings.json` | Per-team UCI/PCS leaderboard for the season |
| `ranking.json` | WT/PRT team ranking, tracked teams flagged |
| `results.json` | All rider results, keyed by rider slug |
| `meta.json` | `generated_at` timestamp (powers "Last updated") |
| `alert_state.json` | Per-race dedup memory for notifications |

---

## Notifications (ntfy)

Pings are spoiler-free — each names only the race ("🚀 Worth watching today: …").

**Subscribe (phone):**
1. Install the **ntfy** app (Android/iOS) or open <https://ntfy.sh>.
2. Subscribe to your topic (a private, hard-to-guess string).

**Wire it up:** add the topic as a GitHub Actions secret named `NTFY_TOPIC`
(Settings → Secrets and variables → Actions). It is never committed. Locally,
`export NTFY_TOPIC=your-topic` before `python -m build.run`. Override the server
with `NTFY_URL` if self-hosting ntfy.

When does it ping (the "worth watching" ladder)?

| Race tier | Pings when a Rockets rider finishes… |
|---|---|
| WorldTour (UWT / Monument / Grand Tour / Worlds / Olympics) | Top 10 |
| ProSeries & Class 1 (1.Pro/2.Pro, 1.1/2.1) | Podium (top 3) |
| Class 2 & U23 (1.2/2.2, 1.2U/2.2U) | Win only |

Plus: **any win in any class always pings.**

---

## Hosting (always-on)

A scheduled GitHub Action (`.github/workflows/scrape.yml`) runs hourly across
16:00–20:00 CEST (and on manual `workflow_dispatch`): it scrapes PCS, exports
the JSON, sends pings, and commits `docs/data/` back to the repo.

Serve the site with **GitHub Pages**: Settings → Pages → Source =
"Deploy from a branch", branch `main`, folder `/docs`. The tracker is then
reachable at `https://<user>.github.io/<repo>/`.

> Scheduled workflows auto-disable after 60 days of repo inactivity (off-season).
> Wake it with a manual `workflow_dispatch` run.

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