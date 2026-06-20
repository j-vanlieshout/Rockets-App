# API Reference

> **Retired (ADR 0001).** The FastAPI server has been removed. The frontend now
> reads static JSON from `docs/data/` produced by `backend/build/export.py`:
> `standings.json`, `ranking.json`, `results.json` (keyed by rider slug), and
> `meta.json`. The shapes below are preserved by the exporter and kept here for
> reference to that data contract.

## Endpoints

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/teams` | — | All tracked teams |
| GET | `/teams/{slug}/riders` | — | Roster, alphabetical |
| GET | `/teams/{slug}/uci-standings` | `?season=` | UCI point leaderboard |
| GET | `/riders/{slug}/results` | `?season=` | Rider season results |
| GET | `/races` | `?season=` | All races with results |
| GET | `/races/{id}/results` | — | Results for one race |
| GET | `/ranking/teams` | `?season=` | Live UCI team ranking (scraped per request) |

## Response schemas

Pydantic models at `backend/api/main.py:56`:

| Schema | Used by |
|--------|---------|
| `TeamOut` | `/teams`, `/teams/{slug}` |
| `RiderOut` | `/teams/{slug}/riders`, `/riders/{slug}` |
| `RiderResultOut` | `/riders/{slug}/results` — extends `ResultOut` with `race_name`, `race_class` |
| `RaceOut` | `/races` |
| `RaceResultOut` | `/races/{id}/results` — extends `ResultOut` with `rider_name`, `rider_nationality` |
| `TeamUCIStandings` | `/teams/{slug}/uci-standings` |
| `TeamRankingOut` | `/ranking/teams` — includes `is_tracked` flag |

## Notes

- Default `season` param: `CURRENT_SEASON` = `datetime.date.today().year` (`config.py:21`)
- `/ranking/teams` hits PCS live; returns HTTP 502 if PCS unreachable (`api/main.py:324`)
- CORS is `allow_origins=["*"]` — required for `file://` to call `localhost:8000`
- `slug` for teams/riders = PCS slug without year, e.g. `unibet-rose-rockets`, `dylan-groenewegen`
