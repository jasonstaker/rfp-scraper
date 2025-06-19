# date_utils.py

import pandas as pd
from datetime import datetime

# requires: date_str is a string, e.g. "4/13/20" or "4/13/20 04:00 MDT"
# modifies: nothing
# effects: returns only the date portion of the input, stripping off any time or timezone
def parse_date_generic(date_str: str) -> str:
    if not isinstance(date_str, str) or not date_str.strip():
        return date_str
    # split on whitespace and keep only the first token (the date)
    return date_str.strip().split()[0]


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
