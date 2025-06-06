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
    "EDT": ZoneInfo("America/New_York"), "EST": ZoneInfo("America/New_York"),
    "ET": ZoneInfo("America/New_York")
}

# requires: date_str is a string (e.g. "Jun 05, 2025 @ 02:30 PM" or any other common format)
# modifies: nothing
# effects: attempts to parse date_str into a datetime object, converts it to the target timezone (PST),
#          and returns it in a canonical format ("YYYY-MM-DD HH:MM:SS"); returns the original string if parsing fails.
def parse_date_generic(date_str: str) -> str:
    if not isinstance(date_str, str) or not date_str.strip():
        return date_str  # return unchanged if not a nonempty string

    cleaned = date_str.strip()

    # Special case: "Jun 05, 2025 @ 02:30 PM"
    try:
        dt_naive = datetime.strptime(cleaned, "%b %d, %Y @ %I:%M %p")
        # Localize as Eastern Time
        dt = dt_naive.replace(tzinfo=ZoneInfo("America/New_York"))
    except ValueError:
        # Fallback to generic parser with tzinfos
        try:
            dt = parser.parse(cleaned, tzinfos=_TZINFOS)
        except (ValueError, OverflowError):
            return date_str  # fallback on parse failure

        # If parsed datetime has no tzinfo, assume Eastern Time
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("America/New_York"))

    # Convert from Eastern Time (or whatever tz identified) to Pacific Time
    dt_in_target = dt.astimezone(_TARGET_ZONE)
    return dt_in_target.strftime(_CANONICAL_FMT)


# requires: date_str is a string
# modifies: nothing
# effects: attempts to parse date_str in MM/DD/YYYY format and returns it in YYYY-MM-DD format; falls back to parse_date_generic if parsing fails
def parse_date_simple(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return parse_date_generic(date_str)

# requires: df is a pandas DataFrame with a 'Due Date' column
# modifies: nothing
# effects: filters the DataFrame to keep only rows where the due date is today or later in the target timezone, returns the filtered DataFrame
def filter_by_dates(df: pd.DataFrame) -> pd.DataFrame:
    tz = ZoneInfo("America/Los_Angeles")

    # make 'today' naive so it can compare with parsed datetimes
    today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    parsed = pd.to_datetime(df['Due Date'], errors='coerce')
    parsed = parsed.dt.tz_localize(None)
    # keep rows whose due date is today or later
    return df[parsed >= today].copy().reset_index(drop=True)