# build/alerts.py
# The "watch-worthiness" core: a pure ping ladder, pure per-race dedup,
# and a thin ntfy.sh notification edge. The pings are spoiler-free —
# they name only the race, never the rider, position, or result.
#
# Bias: too few pings beats too many. Alert fatigue is the failure mode.

import os
import urllib.request


def is_worth_watching(race_class, position) -> bool:
    """Decide whether a result is worth a spoiler-free ping, from the PCS
    race class and finishing position (1 = win).

    Ladder:
      - Any win in any class always pings.
      - WorldTour (UWT / Monument / Grand Tour / Worlds / Olympics): top 10.
      - ProSeries & Class 1 (1.Pro/2.Pro, 1.1/2.1): podium (top 3).
      - Class 2 & U23 and anything unknown/missing: win only.
    """
    if position is None:
        return False
    if position == 1:
        return True
    race_class = race_class.upper() if race_class else ""
    if ("UWT" in race_class or "WORLDTOUR" in race_class or "WORLD CHAMP" in race_class
            or "OLYMP" in race_class or "MONUMENT" in race_class):
        return position <= 10
    if ".PRO" in race_class or race_class.endswith(".1"):
        return position <= 3
    return False


def detect_new_pings(qualifying, alerted_keys):
    """Pure dedup. Given the currently-qualifying results and the set of race
    keys already alerted, return (new_pings, next_state).

    Dedup is per race: multiple qualifying results in the same race produce one
    ping; a race already in `alerted_keys` produces none. `next_state` is the
    full set of alerted race keys after this run (sorted, JSON-friendly).

    Each item in `qualifying` is a dict with at least 'race_key' and 'race_name'.
    """
    alerted = set(alerted_keys)
    new = []
    seen = set()
    for q in qualifying:
        key = q["race_key"]
        if key in alerted or key in seen:
            continue
        seen.add(key)
        new.append({"race_key": key, "race_name": q["race_name"]})
    next_state = sorted(alerted | seen)
    return new, next_state


def find_qualifying(results_by_slug):
    """Scan the exported results map (rider slug -> list of result dicts) and
    return one qualifying entry per race that passes the ladder, deduped by
    race. Each entry: {'race_key': race_id, 'race_name': name}.

    Pure bridge between the JSON export and detect_new_pings — the orchestrator
    feeds the result into the dedup step.
    """
    qualifying = []
    seen = set()
    for results in results_by_slug.values():
        for r in results:
            if not is_worth_watching(r.get("race_class"), r.get("position")):
                continue
            key = r.get("race_id")
            if key in seen:
                continue
            seen.add(key)
            qualifying.append({"race_key": key, "race_name": r.get("race_name")})
    return qualifying


def format_ping_message(race_name) -> str:
    """The spoiler-free notification body — names only the race."""
    return f"🚀 Worth watching today: {race_name}"


def send_ping(race_name, topic=None, base_url=None):
    """Thin ntfy.sh edge (not unit-tested — pure I/O). POSTs a spoiler-free
    message to <base_url>/<topic>. Topic comes from the NTFY_TOPIC env var
    (a GitHub Actions secret); base URL from NTFY_URL (default ntfy.sh).
    Returns False without sending if no topic is configured."""
    topic = topic or os.environ.get("NTFY_TOPIC")
    base_url = (base_url or os.environ.get("NTFY_URL") or "https://ntfy.sh").rstrip("/")
    if not topic:
        return False
    data = format_ping_message(race_name).encode("utf-8")
    req = urllib.request.Request(f"{base_url}/{topic}", data=data, method="POST")
    urllib.request.urlopen(req, timeout=10)
    return True
