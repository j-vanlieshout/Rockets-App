# Rockets Tracker — Agent Guide

Be extremely concise. Sacrifice grammar for concision.
At the end of each plan, list unresolved questions.

**What:** SQLAlchemy + SQLite build-time toolchain; single-file vanilla-JS frontend (`docs/index.html`)
served as static files. Data is exported to JSON (`docs/data/`) — no running server.
Data scraped from ProCyclingStats via `procyclingstats` + `cloudscraper`. Python 3.11.

**Why:** Local tracker for Unibet Rose Rockets (Dutch ProTeam chasing WorldTour). UCI standings,
race results, spoiler-free alerts, WT/PRT ranking. No auth, no cloud.

## Setup

1. `python -m venv .venv && .venv\Scripts\activate` (Windows) or `source .venv/bin/activate`
2. `pip install -r backend/requirements.txt`
3. `pip install -r backend/requirements-dev.txt` (dev only)

## Build + run

No server. Data is static JSON under `docs/data/`, produced at build time.

1. `cd backend`
2. `python db/sync.py` — scrapes PCS for teams in `config.py:9` → `pcs_tracker.db`
3. `python -m build.run` — export DB → `docs/data/*.json` + detect/send pings
4. Open `docs/index.html` in browser — reads `./data/*.json` (same-origin)

In production the GitHub Action does steps 2–3 on a cron and commits the JSON;
GitHub Pages serves `docs/`.

## Test

1. `cd backend`
2. `pytest tests/ -v` — in-memory SQLite, no network calls

## Key files

| File | Role |
|------|------|
| `backend/config.py:9` | Tracked teams, season, DB URL — edit to add a team |
| `backend/db/sync.py:205` | Sync entry point (`sync_all` → `sync_team`) |
| `backend/build/export.py` | DB → `docs/data/*.json` (standings, ranking, results, meta) |
| `backend/build/alerts.py` | Ping ladder, per-race dedup, ntfy edge |
| `backend/build/run.py` | Build orchestrator (scrape → export → detect → ping) |
| `backend/db/models.py:21` | ORM: Team, Rider, Race, RaceResult |
| `docs/index.html` | Entire frontend (CSS + JS inline) |

## Docs

- [docs/api.md](docs/api.md) — Endpoint table, response schemas, slug format; read when touching API or frontend fetch calls
- [docs/architectural_patterns.md](docs/architectural_patterns.md) — Upsert, slug normalization, race-name parsing, live-vs-cached split, data flow, test DB override
- [docs/data-model.md](docs/data-model.md) — Entity schema and PCS URL patterns (aspirational; `db/models.py:21` is authoritative)

## Skills

- [sync-pcs-data](.agents/skills/sync-pcs-data/SKILL.md) — Full sync workflow + troubleshooting (IndexError, 403s, missing race class, idempotency)
- [create-agents-md](.agents/skills/create-agents-md/SKILL.md) — How to write or refactor AGENTS.md for a project
- [delegate-to-ollama](.agents/skills/delegate-to-ollama/SKILL.md) — Offload a coding task to local Ollama `qwen2.5:7b`; integrates with `/tdd` GREEN phase

## Agent skills

### Issue tracker

Issues in GitHub Issues (`github.com/j-vanlieshout/Rockets-App`); skills use the `gh` CLI.
External PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.
See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` at root + `docs/adr/` for decisions. See `docs/agents/domain.md`.
