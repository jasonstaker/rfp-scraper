# data_utils.py

# third-party import
import pandas as pd

# project settings
from scraper.config.settings import KEYWORD_FILE


def filter_by_keywords(df):
    # load keywords from file
    try:
        with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
            keywords = [line.strip().lower() for line in f if line.strip()]
            if (len(keywords) == 0):
                return df
    except FileNotFoundError:
        return pd.DataFrame()

    # nothing to filter or no keywords
    if df.empty or not keywords:
        return pd.DataFrame()

    hits = []
    # count keyword instances for each row
    for idx, row in df[df['Label'].notna()].iterrows():
        text = row['Label'].lower()
        # total occurrences of all keywords in the text
        count = sum(text.count(kw) for kw in keywords)
        if count:
            hits.append((idx, count))

    # no matches found
    if not hits:
        return pd.DataFrame()

    # build filtered dataframe with hit counts
    indices, counts = zip(*hits)
    filtered = df.loc[list(indices)].copy().reset_index(drop=True)
    filtered['Keyword Hits'] = list(counts)

    # sort by hit count descending
    return filtered.sort_values(by='Keyword Hits', ascending=False).reset_index(drop=True)

