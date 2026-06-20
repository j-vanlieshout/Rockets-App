# tests/test_alerts.py
# Pure ping logic: the "worth watching" ladder and per-race dedup.
# No DB, no network — exhaustive table-driven and state-based tests,
# matching the pure-function style of test_sync.py.

import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from build import alerts


@pytest.mark.parametrize("race_class, position, expected", [
    # Universal rule: any win in any class always pings
    ("2.UWT", 1, True),
    ("1.Pro", 1, True),
    ("2.2",   1, True),
    ("2.2U",  1, True),
    ("",      1, True),
    (None,    1, True),
    # WorldTour tier (UWT / Monument / Grand Tour / Worlds-Olympics): top 10
    ("2.UWT", 10, True),
    ("2.UWT", 11, False),
    ("1.UWT", 3,  True),
    # ProSeries & Class 1: podium (top 3)
    ("1.Pro", 3, True),
    ("2.Pro", 3, True),
    ("1.1",   3, True),
    ("2.1",   3, True),
    ("1.1",   4, False),
    ("1.Pro", 5, False),
    # Class 2 & U23: win only (non-win does not ping)
    ("2.2",  2, False),
    ("1.2",  3, False),
    ("2.2U", 3, False),
    ("1.2U", 2, False),
    # Unknown / missing class: safe — win only
    ("???",  5, False),
    ("???",  1, True),
    (None,   5, False),
    ("",     3, False),
])
def test_ladder(race_class, position, expected):
    assert alerts.is_worth_watching(race_class, position) is expected


def test_ladder_handles_missing_position():
    assert alerts.is_worth_watching("2.UWT", None) is False


# ── Per-race dedup ───────────────────────────────────────────────────────────

def test_new_race_produces_ping_and_updates_state():
    qualifying = [{"race_key": "race-a", "race_name": "Race A"}]
    new, next_state = alerts.detect_new_pings(qualifying, alerted_keys=[])
    assert [p["race_name"] for p in new] == ["Race A"]
    assert "race-a" in next_state


def test_already_alerted_race_does_not_ping_again():
    qualifying = [{"race_key": "race-a", "race_name": "Race A"}]
    new, next_state = alerts.detect_new_pings(qualifying, alerted_keys=["race-a"])
    assert new == []
    assert "race-a" in next_state  # state retains it


def test_multiple_races_same_day_ping_once_each():
    qualifying = [
        {"race_key": "race-a", "race_name": "Race A"},
        {"race_key": "race-b", "race_name": "Race B"},
        {"race_key": "race-a", "race_name": "Race A"},  # second rider, same race
    ]
    new, next_state = alerts.detect_new_pings(qualifying, alerted_keys=[])
    assert sorted(p["race_name"] for p in new) == ["Race A", "Race B"]
    assert set(next_state) == {"race-a", "race-b"}


def test_find_qualifying_filters_results_through_ladder():
    """Scans the exported results map (keyed by rider slug) and returns one
    entry per qualifying race, deduped per race, ready for detect_new_pings."""
    results_by_slug = {
        "rider-one": [
            {"race_id": 1, "race_name": "Big Tour", "race_class": "2.UWT", "position": 5},   # WT top10 -> ping
            {"race_id": 2, "race_name": "Small Race", "race_class": "2.2", "position": 4},    # C2 non-win -> no
        ],
        "rider-two": [
            {"race_id": 3, "race_name": "ProSeries Cup", "race_class": "1.Pro", "position": 1},  # win -> ping
            {"race_id": 1, "race_name": "Big Tour", "race_class": "2.UWT", "position": 9},    # same race as r1 -> dedup
        ],
    }
    qualifying = alerts.find_qualifying(results_by_slug)
    keys = sorted(q["race_key"] for q in qualifying)
    assert keys == [1, 3]
    names = {q["race_name"] for q in qualifying}
    assert names == {"Big Tour", "ProSeries Cup"}


def test_message_names_only_the_race():
    msg = alerts.format_ping_message("Clasica de Almeria")
    assert "Clasica de Almeria" in msg
    for leak in ("P1", "1st", "win", "podium", "Rider", "UCI"):
        assert leak.lower() not in msg.lower()
