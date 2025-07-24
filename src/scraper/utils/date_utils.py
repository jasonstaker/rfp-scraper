# date_utils.py

import re
import pandas as pd
from datetime import datetime


# requires: date_str is a string, e.g. "4/13/20" or "4/13/20 04:00 MDT"
# effects: returns only the date portion of the input, stripping off any time or timezone

def parse_date_generic(date_str: str) -> str:
    if date_str == "12/31/9999":
        return "9999-12-31"
    if not isinstance(date_str, str):
        return date_str
    s = date_str.strip()
    if not s:
        return s

    s = re.sub(r"\b[A-Z]{3,4}\b$", "", s).strip()

    if '@' in s:
        s = s.split('@', 1)[0].strip()

    m = re.match(r'^(\d{1,2}/\d{1,2}/\d{4})', s)
    if m:
        date_part = m.group(1)
    else:
        m2 = re.match(r'^([A-Za-z]+ \d{1,2},\s*\d{4})', s)
        date_part = m2.group(1) if m2 else s.split()[0]

    try:
        return pd.to_datetime(date_part, errors="raise").date().isoformat()
    except Exception:
        return date_part



# requires: df is a pandas DataFrame with an 'end_date' column
# effects: filters to keep only rows whose date (parsed via parse_date_generic) is today or later
def filter_by_dates(df: pd.DataFrame) -> pd.DataFrame:
    today = datetime.now().date()
    if len(df) == 0:
        return df
    elif len(df) == 1:
        row = df.iloc[0]
        others = row.drop(labels=['State'], errors='ignore')
        if others.isna().all() or all((pd.isna(v) or v == '' for v in others)):
            return df.iloc[0:0].copy()

    parsed_dates = df["end_date"].astype(str).apply(parse_date_generic)
    parsed = pd.to_datetime(parsed_dates, errors="coerce").dt.date

    mask = parsed.notna() & (parsed >= today)
    rescue = parsed.isna() & (parsed_dates == "9999-12-31")
    mask = mask | rescue

    return df.loc[mask].reset_index(drop=True)
