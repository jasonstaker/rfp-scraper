# data_utils.py

import zipfile
import pandas as pd
import json
from pathlib import Path

# project settings
from src.config import KEYWORDS_FILE, HIDDEN_IDS_FILE, OUTPUT_DIR

# requires: nothing
# modifies: nothing
# effects: loads and returns a set of hidden solicitation ids from a json file, or an empty set if the file is not found or invalid
def load_hidden_ids() -> set[str]:
    try:
        return set(json.loads(Path(HIDDEN_IDS_FILE).read_text(encoding='utf-8')))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

# requires: df is a pandas DataFrame
# modifies: nothing
# effects: filters the DataFrame based on hidden ids and keyword hits, returns a new DataFrame with filtered and sorted records
def filter_by_keywords(df: pd.DataFrame) -> pd.DataFrame:
    # load keywords
    try:
        with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
            keywords = [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        # no keywords file found
        return df

    # nothing to filter
    if df.empty:
        return pd.DataFrame()
    
    if not keywords:
        df = df.copy()
        df['Keyword Hits'] = 0
        return df.reset_index(drop=True)

    # collect keyword hit counts
    hits = []
    for idx, row in df[df['title'].notna()].iterrows():
        text = row['title'].lower()
        count = sum(text.count(kw) for kw in keywords)
        if count:
            hits.append((idx, count))
    if not hits:
        return pd.DataFrame()

    # build filtered dataframe
    indices, counts = zip(*hits)
    filtered = df.loc[list(indices)].copy().reset_index(drop=True)
    filtered['Keyword Hits'] = list(counts)
    return filtered.sort_values(by='Keyword Hits', ascending=False).reset_index(drop=True)

# requires: excel_path is a Path object pointing to an excel file
# modifies: the hidden ids json file
# effects: reads the excel file, extracts hidden solicitation ids, and updates the hidden ids json file with the union of existing and new hidden ids
def sync_hidden_from_excel(
    excel_path: Path = OUTPUT_DIR / "rfp_scraping_output.xlsx"
) -> None:
    # load existing ids
    path = Path(HIDDEN_IDS_FILE)
    try:
        existing = set(json.loads(path.read_text(encoding='utf-8')))
    except (FileNotFoundError, json.JSONDecodeError):
        existing = set()

    # read excel without headers
    try:
        df = pd.read_excel(excel_path, header=None, sheet_name=0, engine="openpyxl")
    except (FileNotFoundError, PermissionError):
        return

    # skip header row, grab hide flag (col 0) and solicitation # (col 3)
    try:
        data = df.iloc[1:, [0, 3]].copy()
        data.columns = ['Hide', 'Solicitation#']
    except IndexError:
        return

    # collect newly hidden ids
    newly = set(data.loc[data['Hide'] == True, 'Solicitation#'].astype(str).tolist())

    # merge and persist
    all_ids = sorted(existing.union(newly))
    path.write_text(json.dumps(all_ids, indent=2), encoding='utf-8')

# requires: df is a pandas DataFrame
# modifies: nothing
# effects: returns a tuple of (visible, hidden) DataFrames
#   visible: rows matching filter_by_keywords AND not manually hidden
#   hidden: all other rows (manually hidden or no keyword hits)
def split_by_keywords(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    # 1) run keyword filter to get all rows with hits
    kw_visible = filter_by_keywords(df)

    # 2) load manual hidden IDs
    hidden_ids = load_hidden_ids()

    # 3) keep only those not manually hidden
    code_col = 'Solicitation #'
    visible = kw_visible.loc[
        ~kw_visible[code_col].astype(str).isin(hidden_ids)
    ].reset_index(drop=True)

    # 4) manual hidden mask
    manual_mask = df[code_col].astype(str).isin(hidden_ids)

    # 5) dropped-by-keyword mask
    dropped_idx = df.index.difference(kw_visible.index)

    # 6) combine to form hidden mask
    hidden_mask = manual_mask.copy()
    hidden_mask.loc[dropped_idx] = True

    # 7) build hidden DataFrame
    hidden = df.loc[hidden_mask].reset_index(drop=True)

    return visible, hidden
