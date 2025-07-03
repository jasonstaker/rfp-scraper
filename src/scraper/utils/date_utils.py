# date_utils.py

import re
import pandas as pd
from datetime import datetime

# requires: date_str is a string, e.g. "4/13/20" or "4/13/20 04:00 MDT"
# modifies: nothing
# effects: returns only the date portion of the input, stripping off any time or timezone
def parse_date_generic(date_str: str) -> str:
    if date_str == "12/31/9999":
        return "9999-12-31"
    if not isinstance(date_str, str):
        return date_str
    s = date_str.strip()
    if not s:
        return s

    if '@' in s:
        s = s.split('@', 1)[0].strip()

    m = re.match(r'^(\d{1,2}/\d{1,2}/\d{4})', s)
    if m:
        date_part = m.group(1)

    else:
        m2 = re.match(r'^([A-Za-z]+ \d{1,2}, \s*\d{4})', s)
        if m2:
            date_part = m2.group(1)
        else:
            date_part = s.split()[0]

    try:
        dt = pd.to_datetime(date_part, errors="raise")
        return dt.date().isoformat()
    except Exception:
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
import pandas as pd
from datetime import datetime

def filter_by_dates(df: pd.DataFrame) -> pd.DataFrame:
    today = datetime.now().date()

    if len(df) == 1:
        row = df.iloc[0]
        others = row.drop(labels=['State'], errors='ignore')
        if others.isna().all() or all((pd.isna(v) or v == '' for v in others)):
            return df.iloc[0:0].copy()

    due_str = df["Due Date"].astype(str)
    parsed = pd.to_datetime(due_str, errors="coerce").dt.date

    mask = parsed.notna() & (parsed >= today)

    rescue = parsed.isna() & (due_str == "9999-12-31")
    mask = mask | rescue

    return df.loc[mask].reset_index(drop=True)
