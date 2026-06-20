# tests/test_export.py
# JSON export: DB -> data structures the frontend consumes.
# Seeds an in-memory SQLite DB and asserts the exported shapes,
# mirroring the db_session seeding style used elsewhere in the suite.

import json
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.models import Base, Team, Rider, Race, RaceResult
from build import export


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()


def _seed(db):
    """A team with two riders: one who scored, one who hasn't raced."""
    team = Team(name="Unibet Rose Rockets", slug="unibet-rose-rockets", uci_code="URR")
    db.add(team)
    db.flush()

    scorer = Rider(pcs_slug="rider-one", full_name="Rider One",
                   nationality="NED", age=24, team_id=team.id)
    idle = Rider(pcs_slug="rider-two", full_name="Rider Two",
                 nationality="BEL", age=28, team_id=team.id)
    db.add_all([scorer, idle])
    db.flush()

    race = Race(pcs_slug="race/2026/result", name="Clasica de Almeria",
                season=2026, race_class="1.Pro")
    db.add(race)
    db.flush()

    db.add(RaceResult(race_id=race.id, rider_id=scorer.id, team_id=team.id,
                      stage="race/2026/result", date="2026-02-15",
                      position=3, pcs_points=50.0, uci_points=125.0))
    db.commit()
    return team, scorer, idle, race


def test_standings_lists_riders_with_totals_and_idle_last(session):
    """Standings carries each rider's UCI/PCS totals; riders who haven't
    raced are included at the bottom with zero points."""
    _seed(session)

    standings = export.build_standings(session, "unibet-rose-rockets", season=2026)

    assert standings["team_name"] == "Unibet Rose Rockets"
    assert standings["season"] == 2026
    assert standings["total_uci_points"] == 125.0

    riders = standings["riders"]
    assert [r["pcs_slug"] for r in riders] == ["rider-one", "rider-two"]

    top = riders[0]
    assert top["full_name"] == "Rider One"
    assert top["total_uci_points"] == 125.0
    assert top["total_pcs_points"] == 50.0
    assert top["results_count"] == 1

    bottom = riders[1]
    assert bottom["pcs_slug"] == "rider-two"
    assert bottom["total_uci_points"] == 0
    assert bottom["results_count"] == 0


def test_results_keyed_by_rider_slug_with_race_metadata(session):
    """results is one combined dict keyed by rider slug; each entry carries
    race name, class, position, date and points."""
    _seed(session)

    results = export.build_results(session, season=2026)

    assert "rider-one" in results
    rider_results = results["rider-one"]
    assert len(rider_results) == 1

    r = rider_results[0]
    assert r["race_name"] == "Clasica de Almeria"
    assert r["race_class"] == "1.Pro"
    assert r["position"] == 3
    assert r["date"] == "2026-02-15"
    assert r["uci_points"] == 125.0
    assert r["pcs_points"] == 50.0

    # A rider with no results does not appear (or appears empty) — must not raise
    assert results.get("rider-two", []) == []


def test_ranking_shapes_scraped_entries_and_flags_tracked():
    """Ranking is shaped from scraped entries; tracked teams are flagged."""
    entries = [
        SimpleNamespace(season=2026, team_name="Big WT Team", team_slug="big-wt-team",
                        team_class="WT", uci_ranking_position=1, prev_rank=2, uci_points=5000.0),
        SimpleNamespace(season=2026, team_name="Unibet Rose Rockets", team_slug="unibet-rose-rockets",
                        team_class="PRT", uci_ranking_position=19, prev_rank=21, uci_points=800.0),
    ]

    ranking = export.build_ranking(entries, tracked_slugs={"unibet-rose-rockets"})

    assert ranking[0]["team_name"] == "Big WT Team"
    assert ranking[0]["current_rank"] == 1
    assert ranking[0]["prev_rank"] == 2
    assert ranking[0]["current_points"] == 5000.0
    assert ranking[0]["is_tracked"] is False

    rockets = ranking[1]
    assert rockets["team_slug"] == "unibet-rose-rockets"
    assert rockets["team_class"] == "PRT"
    assert rockets["is_tracked"] is True


def test_export_all_writes_files_with_timestamp(session, tmp_path):
    """export_all writes the four JSON files; meta carries a generated_at stamp."""
    _seed(session)
    entries = [SimpleNamespace(season=2026, team_name="Unibet Rose Rockets",
                               team_slug="unibet-rose-rockets", team_class="PRT",
                               uci_ranking_position=19, prev_rank=21, uci_points=800.0)]

    export.export_all(session, str(tmp_path), season=2026, ranking_entries=entries,
                      team_slug="unibet-rose-rockets", tracked_slugs={"unibet-rose-rockets"})

    for name in ("standings.json", "ranking.json", "results.json", "meta.json"):
        assert (tmp_path / name).exists(), f"missing {name}"

    standings = json.loads((tmp_path / "standings.json").read_text())
    assert standings["team_name"] == "Unibet Rose Rockets"

    meta = json.loads((tmp_path / "meta.json").read_text())
    assert "generated_at" in meta and meta["generated_at"]
