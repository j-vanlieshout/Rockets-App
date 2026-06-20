---
name: sync-pcs-data
description: Scrape ProCyclingStats for all tracked teams and persist to local SQLite. Use when race results need refreshing, after a new team is added, or after a fresh clone.
---

## When to use

- After clone (DB is gitignored; must be populated before the API can serve data)
- After a race weekend to pick up new results
- After adding a team to `backend/config.py:9`
- To backfill a prior season

## Steps

1. Activate venv: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate`
2. `cd backend`
3. `python db/sync.py` — syncs current season for all teams in `config.py:TRACKED_TEAMS`
4. Optional: `python db/sync.py --season 2025` for a specific season
5. Watch stdout — each team prints `✅ <name>: N riders, M results saved` on success
6. Restart the API if it's already running (`Ctrl-C` then `python -m uvicorn api.main:app`)

## Troubleshooting

**`IndexError` from PCS library** (`db/sync.py:164`)
Rider has an incomplete PCS profile. Logged as WARNING. Rider is saved with roster data
only (name, nationality, age) but no season results. Expected; not a bug.

**HTTP 403 / Cloudflare block**
PCS rate-limits aggressive scrapers. `cloudscraper` handles most cases. Wait 60s and retry.
If persistent, check whether PCS has changed its anti-bot measures.

**Missing race class after sync**
`upsert_race` backfills `race_class` if missing on a previous sync (`db/sync.py:123`).
Re-running sync fixes it automatically.

**Duplicate results**
The `UniqueConstraint("race_id", "rider_id", "stage")` at `db/models.py:72` prevents
duplicate rows. Sync is idempotent — re-running updates existing rows in place.

**Wrong season shown in frontend**
`CURRENT_SEASON` is `datetime.date.today().year` (`config.py:21`). If syncing past data,
pass `--season` explicitly; the frontend's default API calls also use `CURRENT_SEASON`.

## Key entry points

- Sync entry: `db/sync.py:205` (`sync_all`)
- Per-team loop: `db/sync.py:174` (`sync_team`)
- Rider profile fetch with fallback: `db/sync.py:156` (`fetch_rider_profile`)
- Upsert helpers: `db/sync.py:66–152`
