# average_time_manager.py

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

from src.config import PERSISTENCE_DIR

logger = logging.getLogger(__name__)
AVERAGES_FILE = PERSISTENCE_DIR / "averages.json"
_write_lock = threading.Lock()

# effects: returns the dictionary of average times of states and counties
def load_averages() -> Dict[str, Dict]:
    if AVERAGES_FILE.exists():
        try:
            with AVERAGES_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("states", {})
                data.setdefault("counties", {})
                return data
        except json.JSONDecodeError:
            try:
                backup = AVERAGES_FILE.with_suffix(AVERAGES_FILE.suffix + ".corrupt")
                AVERAGES_FILE.replace(backup)
                logger.exception("Corrupted averages file moved to %s", backup)
            except Exception:
                logger.exception("Failed to move corrupted averages file %s", AVERAGES_FILE)
        except Exception:
            logger.exception("Failed to read averages file %s", AVERAGES_FILE)
    return {"states": {}, "counties": {}}

# effects: returns calculated total time
def estimate_total_time(
    averages: Dict[str, Dict],
    states: List[str],
    counties: Optional[Dict[str, List[str]]] = None
) -> Tuple[int, int]:
    total = 0.0
    states_bucket = averages.get("states", {})
    counties_bucket = averages.get("counties", {})

    for st in states:
        total += states_bucket.get(st, {}).get("average_seconds", 0.0)
    if counties:
        for st, clist in counties.items():
            st_bucket = counties_bucket.get(st, {})
            for ct in clist:
                total += st_bucket.get(ct, {}).get("average_seconds", 0.0)
    secs = round(total)
    return secs // 60, secs % 60

# modifies: averages.json
# effects: updates averages based on state and county durations
def update_averages(
    averages: Dict[str, Dict],
    state_durations: Dict[str, float],
    county_durations: Optional[Dict[str, Dict[str, float]]] = None
) -> None:
    averages.setdefault("states", {})
    averages.setdefault("counties", {})

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

    tmp_fd = None
    tmp_path = None
    try:
        with _write_lock:
            fd, tmp_path = tempfile.mkstemp(dir=str(AVERAGES_FILE.parent), prefix="averages.", suffix=".tmp")
            tmp_fd = fd
            with os.fdopen(fd, "w", encoding="utf-8") as tf:
                json.dump(averages, tf, indent=2)
                tf.flush()
                os.fsync(tf.fileno())
            os.replace(tmp_path, str(AVERAGES_FILE))
    except Exception:
        logger.exception("Failed to write averages file %s", AVERAGES_FILE)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                logger.debug("Failed to remove temp file %s", tmp_path)
