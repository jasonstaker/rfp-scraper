# date_utils.py

from datetime import datetime
from zoneinfo import ZoneInfo
from dateutil import parser
import pandas as pd

# target timezone and output format
_TARGET_ZONE = ZoneInfo("America/Los_Angeles")
_CANONICAL_FMT = "%Y-%m-%d %H:%M:%S"

# map common abbreviations to zoneinfo zones
_TZINFOS = {
    "CDT": ZoneInfo("America/Chicago"), "CST": ZoneInfo("America/Chicago"),
    "MDT": ZoneInfo("America/Denver"),  "MST": ZoneInfo("America/Denver"),
    "PDT": ZoneInfo("America/Los_Angeles"), "PST": ZoneInfo("America/Los_Angeles"),
    "EDT": ZoneInfo("America/New_York"), "EST": ZoneInfo("America/New_York")
}

def parse_date_generic(date_str: str) -> str:
    if not isinstance(date_str, str) or not date_str.strip():
        return date_str  # return unchanged if not a nonempty string
    try:
        # pass tzinfos so CDT/PDT/MDT/etc. are recognized
        dt = parser.parse(date_str, tzinfos=_TZINFOS)
    except (ValueError, OverflowError):
        return date_str  # fallback on parse failure
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_TARGET_ZONE)
    dt_in_target = dt.astimezone(_TARGET_ZONE)
    return dt_in_target.strftime(_CANONICAL_FMT)


def parse_date_simple(date_str: str) -> str:
    # first try strict MM/DD/YYYY -> YYYY-MM-DD; else use generic parser.
    try:
        return datetime.strptime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return parse_date_generic(date_str)

def filter_by_dates(df: pd.DataFrame) -> pd.DataFrame:
    tz = ZoneInfo("America/Los_Angeles")

    # make 'today' naive so it can compare with parsed datetimes
    today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    parsed = pd.to_datetime(df['Due Date'], errors='coerce')
    parsed = parsed.dt.tz_localize(None)
    # keep rows whose due date is today or later
    return df[parsed >= today].copy().reset_index(drop=True)

