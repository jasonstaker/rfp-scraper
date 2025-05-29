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

def main():
    # Ensure output directory exists
    output_dir = "./output"
    os.makedirs(output_dir, exist_ok=True)

    # Configure logging to file
    logging.basicConfig(
        level=logging.INFO,
        filename=os.path.join(output_dir, "scraper.log"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logging.info("=" * 80)
    logging.info(f"starting scraper run at {datetime.datetime.now().isoformat()}")
    logging.info("=" * 80)

    # Parse command-line args for states
    parser = argparse.ArgumentParser(description="run multiple scrapers")
    parser.add_argument(
        "--states",
        nargs="+",
        required=True,
        help="states to scrape, or 'all'"
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
            logging.error(f"no scraper(s) found for: {bad}")
    if not to_run:
        return

    output_path = os.path.join(output_dir, "rfq_scraping_output.xlsx")

    # Run each scraper and collect DataFrames into a dictionary
    state_to_df_map = {}
    for state in to_run:
        logging.info(f"[{state}] instantiating scraper")
        scraper = SCRAPER_MAP[state]()
        df = pd.DataFrame(scraper.scrape())
        if df.empty:
            logging.info(f"[{state}] no records found")
            continue
        logging.info(f"[{state}] scraped {len(df)} records")
        state_to_df_map[state] = df

    # Write the combined "All RFPs" sheet using export_all
    try:
        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            export_all(state_to_df_map, writer)
    except Exception as e:
        logging.error(f"failed to write excel output: {e}")
        return

    logging.info(f"exported excel file to {output_path}")
    # Try opening the file after writing (Windows-specific)
    try:
        os.startfile(os.path.abspath(output_path))
    except Exception as e:
        logging.warning(f"could not open the excel file automatically: {e}")

if __name__ == "__main__":
    main()