# date_utils.py

import pandas as pd
from datetime import datetime

# requires: date_str is a string, e.g. "4/13/20" or "4/13/20 04:00 MDT"
# modifies: nothing
# effects: returns only the date portion of the input, stripping off any time or timezone
def parse_date_generic(date_str: str) -> str:
    """
    Normalize a date/time string by stripping off the time and returning
    an ISO-formatted date (YYYY-MM-DD). Supports:
      - 'Jul 31, 2025 @ 03:00 PM'
      - '7/15/2025 4:00:00 PM'
      - plain 'YYYY-MM-DD' or other common date tokens
    Falls back to the raw date part if parsing fails.
    """
    if not isinstance(date_str, str):
        return date_str
    s = date_str.strip()
    if not s:
        return s

    # 1) Drop anything after '@' (e.g. time in 'Jul 31, 2025 @ 03:00 PM')
    if '@' in s:
        date_part = s.split('@', 1)[0].strip()
    else:
        # 2) For numeric date-times like '7/15/2025 4:00:00 PM',
        #    split on whitespace and take only the date token
        date_part = s.split()[0]

    # 3) Try to parse with pandas (infer common formats)
    try:
        dt = pd.to_datetime(date_part, infer_datetime_format=True, errors="raise")
        return dt.date().isoformat()
    except Exception:
        # 4) Fallback: return the raw date part
        return date_part


# requires: date_str is a string, ideally in MM/DD/YYYY or MM/DD/YY format, possibly with time
# modifies: nothing
# effects: returns the date portion as-is if it matches MM/DD/YYYY or MM/DD/YY; otherwise, falls back to parse_date_generic
def parse_date_simple(date_str: str) -> str:
    if not isinstance(date_str, str) or not date_str.strip():
        return date_str
    txt = date_str.strip().split()[0]
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            # reformat to the same pattern to validate
            dt = datetime.strptime(txt, fmt)
            return dt.strftime(fmt)
        except ValueError:
            continue
    # fallback for any other format
    return parse_date_generic(date_str)


# requires: df is a pandas DataFrame with a 'Due Date' column
# modifies: nothing
# effects: filters to keep only rows whose date (parsed via parse_date_generic) is today or later
def filter_by_dates(df: pd.DataFrame) -> pd.DataFrame:
    today = datetime.now().date()
    # extract date strings, parse to date objects
    dates = df["Due Date"].astype(str).apply(parse_date_generic)
    parsed = pd.to_datetime(dates, errors="coerce").dt.date
    return df[parsed >= today].copy().reset_index(drop=True)
