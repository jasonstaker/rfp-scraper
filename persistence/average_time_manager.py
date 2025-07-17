# average_time_manager.py

import json
from pathlib import Path

from src.config import PERSISTENCE_DIR
AVERAGES_FILE = PERSISTENCE_DIR / "averages.json"

# effects: returns the dictionary of average times 
def load_averages() -> dict:
    if AVERAGES_FILE.exists():
        try:
            with open(AVERAGES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

# effects: returns calculated total time 
def estimate_total_time(averages: dict, states: list[str]) -> tuple[int, int]:
    total = sum(averages.get(s, {}).get("average_seconds", 0) for s in states)
    total = round(total)
    return total // 60, total % 60

# modifies: averages.json 
# effects: updates the averages based on state_durations and previosu averages 
def update_averages(averages: dict, state_durations: dict[str, float]):
    for state, dur in state_durations.items():
        entry = averages.get(state, {"count": 0, "average_seconds": 0.0})
        count = entry["count"]
        avg   = entry["average_seconds"]
        new_avg = (avg * count + dur) / (count + 1)
        averages[state] = {"count": count + 1, "average_seconds": new_avg}

    AVERAGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AVERAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(averages, f, indent=2)
