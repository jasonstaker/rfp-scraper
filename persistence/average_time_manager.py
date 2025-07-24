# average_time_manager.py

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config import PERSISTENCE_DIR

AVERAGES_FILE = PERSISTENCE_DIR / "averages.json"

# effects: returns the dictionary of average times of states and counties
def load_averages() -> Dict[str, Dict]:
    if AVERAGES_FILE.exists():
        try:
            with open(AVERAGES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("states", {})
                data.setdefault("counties", {})
                return data
        except Exception:
            pass
    return {"states": {}, "counties": {}}

# effects: returns calculated total time
def estimate_total_time(
    averages: Dict[str, Dict],
    states: List[str],
    counties: Optional[Dict[str, List[str]]] = None
) -> Tuple[int, int]:
    total = 0.0
    for st in states:
        total += averages["states"].get(st, {}).get("average_seconds", 0.0)
    if counties:
        for st, clist in counties.items():
            for ct in clist:
                total += averages["counties"].get(st, {}).get(ct, {}).get("average_seconds", 0.0)
    secs = round(total)
    return secs // 60, secs % 60

# modifies: averages.json
# effects: updates averages based on state and county durations
def update_averages(
    averages: Dict[str, Dict],
    state_durations: Dict[str, float],
    county_durations: Optional[Dict[str, Dict[str, float]]] = None
) -> None:
    for st, dur in state_durations.items():
        entry = averages["states"].get(st, {"count": 0, "average_seconds": 0.0})
        cnt, avg = entry["count"], entry["average_seconds"]
        averages["states"][st] = {"count": cnt + 1, "average_seconds": (avg * cnt + dur) / (cnt + 1)}
    if county_durations:
        for st, cmap in county_durations.items():
            bucket = averages["counties"].setdefault(st, {})
            for ct, dur in cmap.items():
                entry = bucket.get(ct, {"count": 0, "average_seconds": 0.0})
                cnt, avg = entry["count"], entry["average_seconds"]
                bucket[ct] = {"count": cnt + 1, "average_seconds": (avg * cnt + dur) / (cnt + 1)}
    AVERAGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AVERAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(averages, f, indent=2)
