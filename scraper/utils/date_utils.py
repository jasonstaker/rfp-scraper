# date_utils.py
from datetime import datetime
from zoneinfo import ZoneInfo

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return date_str

def convert_to_pst(raw_date_str: str) -> str:
    try:
        naive_part, _tz_abbrev = raw_date_str.rsplit(" ", 1)
    except ValueError:
        # If the string doesn’t split into two parts, return it unchanged
        return raw_date_str

    # Parse the date-time portion without its zone
    try:
        dt_naive = datetime.strptime(naive_part, "%m/%d/%Y %I:%M %p")
    except ValueError:
        # If parsing fails, return the original string
        return raw_date_str

    # Localize naïve datetime to Mountain time (America/Denver)
    mountain_tz = ZoneInfo("America/Denver")
    dt_mountain = dt_naive.replace(tzinfo=mountain_tz)

    # Convert from Mountain time to Pacific time (America/Los_Angeles)
    pacific_tz = ZoneInfo("America/Los_Angeles")
    dt_pacific = dt_mountain.astimezone(pacific_tz)

    # Format back to "MM/DD/YYYY hh:mm AM/PM TZ"
    return dt_pacific.strftime("%m/%d/%Y %I:%M %p %Z")