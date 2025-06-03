# main.py

# standard library imports
import argparse
import datetime
import os
import logging

# third-party imports
import pandas as pd

# project imports
from scraper.scrapers import SCRAPER_MAP
from scraper.exporters.excel_exporter import export_all
from scraper.utils.data_utils import sync_hidden_from_excel
from scraper.logging_config import configure_logging

def main():
    # Ensure output directory exists
    output_dir = "./output"
    os.makedirs(output_dir, exist_ok=True)

    # log session separation
    log_file = os.path.join(output_dir, "scraper.log")
    with open(log_file, 'a') as f:
        f.write('\n')

    # Suppress WDM and TF logs
    os.environ['WDM_LOG'] = "0"
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = "3"

    # sync hidden rfps (unchanged)
    sync_hidden_from_excel()

    # Configure logging (moved to logging_config.py)
    log_file = os.path.join(output_dir, "scraper.log")
    configure_logging(log_file)

    logging.info("=" * 80)
    logging.info(f"Starting scraper run at {datetime.datetime.now().isoformat()}")
    logging.info("=" * 80)

    # Parse command-line args for states
    parser = argparse.ArgumentParser(description="Run multiple scrapers")
    parser.add_argument(
        "--states",
        nargs="+",
        required=True,
        help="States to scrape, or 'all'"
    )
    args = parser.parse_args()

    # Determine which scrapers to run
    requested = [s.lower() for s in args.states]
    if "all" in requested:
        to_run = list(SCRAPER_MAP.keys())
    else:
        to_run = [s for s in requested if s in SCRAPER_MAP]
        bad = [s for s in requested if s not in SCRAPER_MAP]
        if bad:
            logging.error(f"No scraper(s) found for: {bad}")
    if not to_run:
        return

    output_path = os.path.join(output_dir, "rfp_scraping_output.xlsx")

    # Run each scraper and collect DataFrames into a dictionary
    state_to_df_map = {}
    for state in to_run:
        logging.info(f"[{state}] Instantiating scraper")
        scraper = SCRAPER_MAP[state]()
        df = pd.DataFrame(scraper.scrape())
        if df.empty:
            logging.info(f"[{state}] No records found")
            continue
        logging.info(f"[{state}] Scraped {len(df)} records")
        state_to_df_map[state] = df

    # Write the combined "All RFPs" sheet using export_all
    try:
        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            export_all(state_to_df_map, writer)
    except Exception as e:
        logging.error(f"Failed to write Excel output: {e}")
        return

    logging.info(f"Exported Excel file to {output_path}")
    # Try opening the file after writing (Windows-specific)
    try:
        os.startfile(os.path.abspath(output_path))
    except Exception as e:
        logging.warning(f"Could not open the Excel file automatically: {e}")

if __name__ == "__main__":
    main()