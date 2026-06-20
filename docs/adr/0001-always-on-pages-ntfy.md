# ADR 0001 — Always-on tracker via GitHub Actions + Pages + ntfy

**Status:** Accepted (2026-06-20)

**Supersedes:** the "No cloud" stance in `AGENTS.md` (the *Why* line). The app
remains auth-free and free-to-run, but it is no longer laptop-only.

## Context

The original app works locally but fails its own promise on two fronts:

1. **Hassle to use.** It only runs after manually starting uvicorn, opening
   `docs/index.html`, and running `python db/sync.py`. The owner wants to
   *glance* at it from an Android phone, no ceremony, always current.
2. **Alerts don't alert.** The "Alerts" tab is a page you must open; nothing
   reaches the phone. The "Sync" button doesn't even scrape — it re-fetches the
   API. And `generateAlerts()` labels *every* result "notable", so there is no
   selectivity.

The real product is a **watch-worthiness signal**: a spoiler-free ping that
says *which race recap is worth watching tonight* — without revealing the
result. If no ping arrives, the owner just browses results later at leisure.

## Decision

**Retrofit, not rebuild.** Keep the frontend; replace the plumbing.

### Architecture

- A **GitHub Action** runs on a cron covering **16:00–20:00 CEST** (scheduled in
  UTC; race season Mar–Oct, winter DST shift ignored — no racing then). Each run:
  scrape PCS → export JSON into `docs/data/` → detect new podium-class results →
  fire ntfy → commit the JSON back to the repo.
- **Frontend stays** (`docs/index.html`), served on **GitHub Pages**. Fetch
  calls move from `http://localhost:8000/...` to relative `./data/*.json`.
  Reachable from the phone at a URL.
- **FastAPI retires** — `backend/api/main.py`, the uvicorn entry, and the fake
  "Sync" button are deleted. The scraper (`backend/db/sync.py`, `backend/scraper/`)
  and ORM models are **reused as build-time tools**: scrape into a scratch DB,
  then export JSON.

### Alert

- **Channel:** ntfy.sh. Topic stored as a **GitHub Actions secret** — never in
  the public repo. The Action publishes; the phone subscribes.
- **Content:** **race name only** — e.g. "🚀 Worth watching today: \<race\>".
  Who / what place / win-vs-podium stays a surprise for the recap.
- **Dedup:** per race, via a committed state file. Each qualifying result pings
  exactly once. Multiple races in a day → multiple pings (one per race).

### Ping trigger ("worth watching")

Universal rule: **any win, any class, always pings.** On top of that, a tiered
ladder for non-wins:

| Race tier | Pings when a Rockets rider finishes… |
|---|---|
| **WorldTour** (UWT, Monument, Grand Tour, Worlds/Olympics) | **Top 10** |
| **ProSeries & Class 1** (1.Pro/2.Pro, 1.1/2.1) | **Podium (top 3)** |
| **Class 2 & U23** (1.2/2.2, 1.2U/2.2U) | **Win only (1st)** |

Rationale: the failure mode is alert fatigue. Bias toward too few pings — a
quiet Top-15 in a small race is not a YouTube-recap moment, and one noisy week
trains the owner to ignore the buzz, killing the whole app.

## Consequences

- No server to keep alive; `$0` (public repo → unlimited Action minutes, free
  Pages). Phone just opens a URL.
- The live `/ranking/teams` on-demand scrape becomes part of the scheduled run —
  ranking is only as fresh as the last scrape (acceptable).
- **Off-season sleep:** GitHub disables scheduled workflows after 60 days of repo
  inactivity. Accepted — wake it manually each February. No keep-alive job.
- Scraped JSON is publicly readable on Pages. Acceptable — it is all public PCS
  data anyway.
- The dead "Sync" button becomes a passive **"Last updated: \<time\>"** label.
- JSON shape: one combined `results.json` keyed by rider slug (data is tiny).

## Open questions

None blocking. Revisit the ping ladder after a few race weekends — if it feels
too quiet or too noisy in practice, adjust the thresholds, not the architecture.
