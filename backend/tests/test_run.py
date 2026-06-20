# tests/test_run.py
# The build orchestrator's testable core: alert processing with persisted
# per-race state. The send function is injected, so no network is touched.
# (The scrape + export + git-commit edges are thin I/O and not unit-tested.)

import json

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from build import run


def _results():
    return {
        "rider-one": [
            {"race_id": 1, "race_name": "Big Tour", "race_class": "2.UWT", "position": 4},
            {"race_id": 2, "race_name": "Tiny Race", "race_class": "2.2", "position": 5},
        ],
    }


def test_process_alerts_sends_new_and_persists_state(tmp_path):
    state = tmp_path / "alert_state.json"
    sent = []

    new = run.process_alerts(_results(), str(state), send_fn=lambda name: sent.append(name))

    assert sent == ["Big Tour"]                      # qualifying race pinged
    assert [p["race_name"] for p in new] == ["Big Tour"]
    saved = json.loads(state.read_text())
    assert 1 in saved                                # state remembers the race


def test_process_alerts_is_idempotent_across_runs(tmp_path):
    state = tmp_path / "alert_state.json"
    sent = []
    send = lambda name: sent.append(name)

    run.process_alerts(_results(), str(state), send_fn=send)
    run.process_alerts(_results(), str(state), send_fn=send)   # re-scrape, same data

    assert sent == ["Big Tour"]                      # pinged exactly once


def test_load_state_missing_file_is_empty(tmp_path):
    assert run.load_state(str(tmp_path / "nope.json")) == []
