# Architectural Patterns

## 1. Upsert pattern (all sync entities)

Every entity uses the same shape: query by stable key → create if missing → update mutable
fields → `flush()`. Commit only after all a rider's data is written.

```
upsert_team   → keyed on slug           db/sync.py:66
upsert_rider  → keyed on pcs_slug       db/sync.py:78
upsert_race   → keyed on race_slug      db/sync.py:103
upsert_result → keyed on (race, rider, stage)  db/sync.py:128
```

Stable keys are immutable PCS identifiers. Mutable fields (names, points, race class) are
overwritten on every sync. `flush()` after each entity to get the PK before the next FK
reference; `db.commit()` once per rider at `db/sync.py:200`.

`RaceResult` has a `UniqueConstraint("race_id", "rider_id", "stage")` at the DB level as
a safety net (`db/models.py:72`).

## 2. PCS slug normalization

PCS embeds the year in team slugs and stage paths; these must be stripped to get stable
cross-season identifiers.

**Team slug** — strip trailing year segment:
`"unibet-rose-rockets-2026"` → `"unibet-rose-rockets"` (`uci_ranking.py:47`)

**Stage URL → race slug** — take first 3 path parts:
`"race/tour-de-france/2026/stage-1"` → `"race/tour-de-france/2026"` (`db/sync.py:105`)

**Rider slug** — last segment of PCS `rider_url`:
`"rider/dylan-groenewegen"` → `"dylan-groenewegen"` (`db/sync.py:79`)

## 3. Race name / class extraction

PCS often embeds the race class in the stage name as a trailing parenthetical:
`"Clasica de Almeria (1.Pro)"` → name `"Clasica de Almeria"`, class `"1.Pro"`.

Handled by `extract_class_from_name()` at `db/sync.py:40`. Fallback: use the `class`
field from the result row if the name carries none. If class was missing on a prior sync,
`upsert_race` backfills it on the next run (`db/sync.py:123`).

Stage name prefixes (`"S3Stage 3 - Bessèges › Bessèges"`) are also stripped by
`clean_stage_name()` at `db/sync.py:52`.

## 4. Live vs cached data split

| Data | Source | When fetched |
|------|--------|--------------|
| Teams, riders, races, results | SQLite (`pcs_tracker.db`) | Read from DB on every API request |
| UCI team ranking | PCS (live HTTP) | Scraped on every `GET /ranking/teams` call |

The ranking is live because it changes daily between race days. Rider/result data is only
updated when `sync.py` is run manually. There is no background refresh job.

Live scraping is isolated to `scraper/uci_ranking.py:33`; if PCS is unreachable the
endpoint returns HTTP 502 (`api/main.py:324`).

## 5. Data flow

```
PCS website
  └─ procyclingstats lib + cloudscraper
       ├─ db/sync.py (manual run) ──► pcs_tracker.db (SQLite)
       │                                    └─ api/main.py (FastAPI) ──► docs/index.html
       └─ scraper/uci_ranking.py ──────────► api/main.py /ranking/teams (live, no cache)
```

`pcs_tracker.db` is gitignored — populate via `sync.py` after clone.

## 6. Test DB dependency override

FastAPI's `Depends(get_db)` is replaced in tests via `app.dependency_overrides`:

```
test_api.py:56-59
  app.dependency_overrides[get_db] = lambda: db_session
```

`db_session` is an in-memory SQLite session seeded with a small fixed dataset per test
function. Overrides are cleared in teardown. This pattern means all integration tests are
hermetic — no file DB, no PCS network calls.

The `conftest.py` at `backend/conftest.py:1` only adds `backend/` to `sys.path`; all
fixture logic lives in `tests/test_api.py`.
