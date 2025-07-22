# runner.py

import logging
import datetime
from pathlib import Path
import pandas as pd
import threading
import time

from scraper.scrapers.states import SCRAPER_MAP as STATE_SCRAPERS
from scraper.scrapers.counties import SCRAPER_MAP as COUNTY_SCRAPERS
from scraper.exporters.excel_exporter import export_all
from scraper.utils.data_utils import sync_hidden_from_excel
from src.config import CACHE_DIR, DEFAULT_TIMEOUT, KEYWORDS_FILE, OUTPUT_DIR

# requires: states is a list of state names to scrape, keywords is a list of keywords for filtering, cancel_event is an optional threading.Event to signal cancellation
# modifies: writes to KEYWORDS_FILE, modifies CACHE_DIR by deleting old excel files and writing a new excel file
# effects: writes keywords to KEYWORDS_FILE, runs scrapers for each state, collects and filters records, writes results to a timestamped excel file in CACHE_DIR, and returns both the state→DataFrame map and the file path; raises RuntimeError if scraping is canceled or no records are scraped
def run_scraping(
    states: list[str],
    keywords: list[str],
    counties: dict[str, list[str]] | None = None,
    cancel_event: threading.Event | None = None
) -> tuple[
    dict[str, pd.DataFrame],  # state_to_df
    dict[str, pd.DataFrame],  # county_to_df
    Path,                   # excel file path
    dict[str, float],       # state durations
    dict[str, float]        # county durations
]:
    KEYWORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(KEYWORDS_FILE, "w", encoding="utf-8") as kw_file:
        for kw in keywords:
            kw_file.write(f"{kw}\n")
    logging.info(f"Wrote {len(keywords)} keyword(s) to {KEYWORDS_FILE}")

    if cancel_event is None:
        cancel_event = threading.Event()

    sync_hidden_from_excel()

    state_durations: dict[str, float] = {}
    county_durations: dict[str, float] = {}

    state_to_df: dict[str, pd.DataFrame] = {}
    for state in states:
        if cancel_event.is_set():
            logging.info(f"Cancellation requested before starting state [{state}].")
            break
        logging.info(f"[{state}] Starting scrape...")
        df, elapsed = _run_single_scraper(state, STATE_SCRAPERS, cancel_event)
        state_to_df[state] = df
        state_durations[state] = elapsed

    county_to_df: dict[str, pd.DataFrame] = {}
    if counties:
        for state, county_list in counties.items():
            for county in county_list:
                key = f"{state}:{county}"
                if cancel_event.is_set():
                    logging.info(f"Cancellation requested before starting county [{key}].")
                    break
                logging.info(f"[{key}] Starting scrape...")
                
                df, elapsed = _run_single_scraper(county, COUNTY_SCRAPERS.get(state, {}), cancel_event)
                county_to_df[key] = df
                county_durations[key] = elapsed

    
    if cancel_event.is_set():
        raise RuntimeError("Scrape was canceled by user.")

    if not state_to_df and not county_to_df:
        raise RuntimeError("No records scraped for any state or county.")

    
    all_files = sorted(
        [p for p in CACHE_DIR.iterdir() if p.suffix.lower() == ".xlsx"],
        key=lambda p: p.stat().st_mtime
    )
    if len(all_files) >= 5:
        for old in all_files[:-5]:
            try:
                old.unlink()
                logging.info(f"Deleted old cache file: {old.name}")
            except Exception as e:
                logging.warning(f"Failed to delete {old.name}: {e}")

    
    export_map: dict[str, pd.DataFrame] = {}
    
    for name, df in state_to_df.items():
        if hasattr(df, 'columns') and 'success' in df.columns:
            if df.shape[0] == 1 and df['success'].iat[0] and df.drop(columns=['success']).isna().all(axis=None):
                logging.info(f"Skipping export for empty results of [state {name}]")
                continue
        export_map[name] = df
    
    for name, df in county_to_df.items():
        if hasattr(df, 'columns') and 'success' in df.columns:
            if df.shape[0] == 1 and df['success'].iat[0] and df.drop(columns=['success']).isna().all(axis=None):
                logging.info(f"Skipping export for empty results of [county {name}]")
                continue
        export_map[name] = df

    
    now = datetime.datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    filename = f"rfp_scraping_output_{ts}.xlsx"
    cache_path = CACHE_DIR / filename

    if export_map:
        with pd.ExcelWriter(cache_path, engine="xlsxwriter") as writer:
            export_all(export_map, writer)
        logging.info(f"Saved new cache file: {cache_path.name}")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        desktop_path = OUTPUT_DIR / "rfp_scraping_output.xlsx"
        with pd.ExcelWriter(desktop_path, engine="xlsxwriter") as writer:
            export_all(export_map, writer)
        logging.info(f"Saved new desktop file: {desktop_path.name}")

    return state_to_df, county_to_df, cache_path, state_durations, county_durations


def _run_single_scraper(
    key: str,
    scraper_map: dict[str, type],
    cancel_event: threading.Event
) -> tuple[pd.DataFrame, float]:
    start = time.perf_counter()
    records: list[dict] = []
    success = False

    for attempt in range(1, 4):
        if cancel_event.is_set():
            break
        scraper_cls = scraper_map.get(key)
        if not scraper_cls:
            logging.error(f"No scraper for key [{key}]")
            break
        scraper = scraper_cls()
        try:
            records = scraper.scrape(timeout=DEFAULT_TIMEOUT)
            success = True
            break
        except Exception as e:
            logging.error(f"[{key}] attempt {attempt} failed: {e}")
        finally:
            scraper.close()

    if not success:
        df = pd.DataFrame([{
            'title': None, 'code': None, 'end_date': None,
            'Keyword Hits': None, 'link': None, 'success': False
        }])
    else:
        df = pd.DataFrame(records) if records else pd.DataFrame([{
            'title': None, 'code': None, 'end_date': None,
            'Keyword Hits': None, 'link': None, 'success': True
        }])
        df['success'] = True

    elapsed = time.perf_counter() - start
    return df, elapsed
