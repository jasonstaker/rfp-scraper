# runner.py

import logging
import datetime
from pathlib import Path
import pandas as pd
import threading

from scraper.scrapers import SCRAPER_MAP
from scraper.exporters.excel_exporter import export_all
from scraper.utils.data_utils import sync_hidden_from_excel
from src.config import CACHE_DIR, DEFAULT_TIMEOUT

def run_scraping(
    states: list[str],
    cancel_event: threading.Event | None = None
) -> Path:

    # if no Event was provided, use a dummy Event that never gets set.
    if cancel_event is None:
        cancel_event = threading.Event()

    # sync any “hidden” RFPs
    sync_hidden_from_excel()

    # run each scraper
    state_to_df: dict[str, pd.DataFrame] = {}
    for state in states:
        # Check for cancellation before starting this state
        if cancel_event.is_set():
            logging.info(f"Cancellation requested before starting [{state}]. Exiting.")
            break

        logging.info(f"[{state}] Starting scrape…")
        records: list[dict] = []
        success = False

        for attempt in range(1, 4):
            # check for cancellation before each attempt
            if cancel_event.is_set():
                logging.info(f"Cancellation requested during [{state}] attempt {attempt}.")
                break

            scraper = SCRAPER_MAP[state]()
            try:
                scraped = scraper.scrape(timeout=DEFAULT_TIMEOUT)
                records = scraped
                success = True
                break
            except Exception as e:
                logging.error(f"[{state}] attempt {attempt} failed: {e}")
                if attempt < 3:
                    logging.info(f"[{state}] Retrying (attempt {attempt + 1})…")
                else:
                    logging.error(f"[{state}] All 3 attempts failed.")
            finally:
                scraper.close()

            # check for cancellation after an attempt finishes
            if cancel_event.is_set():
                logging.info(f"Cancellation requested just after [{state}] attempt {attempt}.")
                break

        if not success or cancel_event.is_set():
            # either all attempts failed or cancel was requested mid-state
            continue

        # build DataFrame for this state
        df = pd.DataFrame(records)
        if df.empty:
            logging.info(f"[{state}] No records found.")
            continue

        logging.info(f"[{state}] Scraped {len(df)} records.")
        state_to_df[state] = df

    # if the user hit “Cancel” at any point, stop here
    if cancel_event.is_set():
        raise RuntimeError("Scrape was canceled by user.")

    if not state_to_df:
        raise RuntimeError("No records scraped for any state.")

    # enforce “only latest 5 .xlsx” in CACHE_DIR
    cache_dir: Path = CACHE_DIR
    all_files = sorted(
        [p for p in cache_dir.iterdir() if p.suffix.lower() == ".xlsx"],
        key=lambda p: p.stat().st_mtime
    )
    if len(all_files) >= 5:
        to_delete = all_files[:-5]  # keep the 5 newest, delete the rest
        for old in to_delete:
            try:
                old.unlink()
                logging.info(f"Deleted old cache file: {old.name}")
            except Exception as e:
                logging.warning(f"Failed to delete {old.name}: {e}")

    # write a new timestamped Excel file
    now = datetime.datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    filename = f"rfp_scraping_output_{ts}.xlsx"
    cache_path = cache_dir / filename

    with pd.ExcelWriter(cache_path, engine="xlsxwriter") as writer:
        export_all(state_to_df, writer)

    logging.info(f"Saved new cache file: {cache_path.name}")
    return cache_path
