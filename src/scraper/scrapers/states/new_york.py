# new_york.py
# url: https://ogs.ny.gov/procurement/bid-opportunities

import logging
from urllib.parse import urljoin

import requests
import pandas as pd
from bs4 import BeautifulSoup

from scraper.core.requests_scraper import RequestsScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for New York RFP data using Requests
class NewYorkScraper(RequestsScraper):

    # modifies: self
    # effects: initializes the scraper with New York bid-opportunities URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("new york"))
        self.logger = logging.getLogger(__name__)


    # effects: performs GET to fetch the bid opportunities page; returns HTML text
    def search(self, **kwargs):
        self.logger.info("Fetching New York bid opportunities page")
        try:
            resp = self.session.get(self.base_url, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error: {re}", exc_info=False)
            raise SearchTimeoutError("New York search HTTP error") from re
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("New York search failed") from e


    # requires: html is the HTML of the page containing exactly one bids table
    # effects: uses pandas to locate the table, then BeautifulSoup to extract links, returns list of records
    def extract_data(self, html: str):
        try:
            tables = pd.read_html(html, match="Bid Calendar")
            if not tables:
                self.logger.error("No table found with pandas.read_html")
                raise DataExtractionError("New York extract_data failed: no table")

            df = tables[0]

            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table")
            if not table:
                self.logger.error("No <table> element found in HTML")
                raise DataExtractionError("New York extract_data failed: table element missing")

            rows = table.find_all("tr")[1:]
            records = []
            for idx, row in enumerate(rows):
                try:
                    desc = str(df.iloc[idx, 0]).strip()
                    raw_date = str(df.iloc[idx, 1]).strip()
                    code = str(df.iloc[idx, 2]).strip()

                    a = row.find("a")
                    href = a.get("href") if a else ""
                    full_link = href if href.lower().startswith("http") else urljoin(self.base_url, href)

                    end_date = parse_date_generic(raw_date)

                    records.append({
                        "title": desc,
                        "code": code,
                        "end_date": end_date,
                        "link": full_link,
                    })
                except Exception as e:
                    self.logger.warning(f"extract_data entry parsing failed at row {idx}: {e}", exc_info=False)
                    continue

            return records
        except DataExtractionError:
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("New York extract_data failed") from e


    # effects: orchestrates GET -> extract_data -> filtering; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for New York")
        try:
            html = self.search(**kwargs)
            raw = self.extract_data(html)

            df = pd.DataFrame(raw)
            self.logger.info(f"Total raw records before filtering: {len(df)}")

            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")

            return filtered.to_dict("records")
        except (SearchTimeoutError, DataExtractionError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"New York scrape failed: {e}", exc_info=True)
            raise ScraperError("New York scrape failed") from e
