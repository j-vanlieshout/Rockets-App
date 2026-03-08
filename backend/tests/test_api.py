# tests/test_api.py
# Integration tests for the FastAPI endpoints — uses an in-memory SQLite DB.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.main import app, get_db
from db.models import Base, Team, Rider, Race, RaceResult


# ── In-memory DB fixture ───────────────────────────────────────────────────────

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture()
def db_session():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed data
    team = Team(id=1, name="Unibet Rose Rockets", slug="unibet-rose-rockets", uci_code="URR")
    session.add(team)

    rider1 = Rider(id=1, pcs_slug="dylan-groenewegen", full_name="Dylan Groenewegen",
                   nationality="NED", age=31, team_id=1,
                   sp_one_day_races=0, sp_gc=0, sp_time_trial=0,
                   sp_sprint=95, sp_climber=0, sp_hills=0)
    rider2 = Rider(id=2, pcs_slug="axel-laurance", full_name="Axel Laurance",
                   nationality="FRA", age=23, team_id=1,
                   sp_one_day_races=0, sp_gc=0, sp_time_trial=0,
                   sp_sprint=0, sp_climber=0, sp_hills=0)
    session.add_all([rider1, rider2])

    race = Race(id=1, pcs_slug="race/clasica-de-almeria/2026",
                name="Clasica de Almeria", season=2026, race_class="1.Pro")
    session.add(race)

    result = RaceResult(id=1, race_id=1, rider_id=1, team_id=1,
                        stage="race/clasica-de-almeria/2026/result",
                        date="2026-02-15", position=1,
                        pcs_points=100.0, uci_points=70.0)
    session.add(result)
    session.commit()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── /teams ─────────────────────────────────────────────────────────────────────

class TestTeamsEndpoint:
    def test_list_teams_returns_200(self, client):
        r = client.get("/teams")
        assert r.status_code == 200

    def test_list_teams_contains_rockets(self, client):
        data = client.get("/teams").json()
        assert any(t["slug"] == "unibet-rose-rockets" for t in data)

    def test_get_team_by_slug(self, client):
        r = client.get("/teams/unibet-rose-rockets")
        assert r.status_code == 200
        assert r.json()["uci_code"] == "URR"

    def test_get_team_not_found(self, client):
        r = client.get("/teams/nonexistent-team")
        assert r.status_code == 404


# ── /teams/{slug}/riders ───────────────────────────────────────────────────────

class TestRidersEndpoint:
    def test_get_team_riders_returns_200(self, client):
        r = client.get("/teams/unibet-rose-rockets/riders")
        assert r.status_code == 200

    def test_riders_sorted_alphabetically(self, client):
        data = client.get("/teams/unibet-rose-rockets/riders").json()
        names = [r["full_name"] for r in data]
        assert names == sorted(names)

    def test_get_rider_by_slug(self, client):
        r = client.get("/riders/dylan-groenewegen")
        assert r.status_code == 200
        assert r.json()["nationality"] == "NED"

    def test_rider_not_found(self, client):
        r = client.get("/riders/nobody")
        assert r.status_code == 404


# ── /teams/{slug}/uci-standings ───────────────────────────────────────────────

class TestUCIStandings:
    def test_standings_returns_200(self, client):
        r = client.get("/teams/unibet-rose-rockets/uci-standings?season=2026")
        assert r.status_code == 200

    def test_standings_totals_correct(self, client):
        data = client.get("/teams/unibet-rose-rockets/uci-standings?season=2026").json()
        assert data["total_uci_points"] == 70.0

    def test_standings_includes_zero_point_riders(self, client):
        data = client.get("/teams/unibet-rose-rockets/uci-standings?season=2026").json()
        # rider2 (Laurance) has no results — should still appear
        slugs = [r["pcs_slug"] for r in data["riders"]]
        assert "axel-laurance" in slugs

    def test_standings_sorted_uci_desc(self, client):
        data = client.get("/teams/unibet-rose-rockets/uci-standings?season=2026").json()
        points = [r["total_uci_points"] for r in data["riders"]]
        assert points == sorted(points, reverse=True)

    def test_standings_team_not_found(self, client):
        r = client.get("/teams/nobody/uci-standings")
        assert r.status_code == 404


# ── /riders/{slug}/results ────────────────────────────────────────────────────

class TestRiderResults:
    def test_results_returns_200(self, client):
        r = client.get("/riders/dylan-groenewegen/results?season=2026")
        assert r.status_code == 200

    def test_result_includes_race_name_and_class(self, client):
        data = client.get("/riders/dylan-groenewegen/results?season=2026").json()
        assert len(data) == 1
        assert data[0]["race_name"]  == "Clasica de Almeria"
        assert data[0]["race_class"] == "1.Pro"

    def test_wrong_season_returns_empty(self, client):
        data = client.get("/riders/dylan-groenewegen/results?season=2025").json()
        assert data == []


# ── /races ────────────────────────────────────────────────────────────────────

class TestRacesEndpoint:
    def test_list_races_returns_200(self, client):
        r = client.get("/races?season=2026")
        assert r.status_code == 200

    def test_race_has_class(self, client):
        data = client.get("/races?season=2026").json()
        assert data[0]["race_class"] == "1.Pro"

    def test_get_race_results(self, client):
        r = client.get("/races/1/results")
        assert r.status_code == 200
        assert r.json()[0]["rider_name"] == "Dylan Groenewegen"

    def test_race_not_found(self, client):
        r = client.get("/races/9999/results")
        assert r.status_code == 404