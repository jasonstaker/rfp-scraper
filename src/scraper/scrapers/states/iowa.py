# iowa.py
# url: https://bidopportunities.iowa.gov/

import logging
import time
import re
import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from scraper.core.requests_scraper import RequestsScraper
from src.config import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic

from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Iowa RFP data using Requests
class IowaScraper(RequestsScraper):

    # modifies: self
    # effects: initializes the scraper with Iowa's hosted bids search URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP['iowa'])
        self.logger = logging.getLogger(__name__)


    # effects: issues a GET to the Iowa hosted bids search endpoint; returns JSON or raises
    def search(self, **kwargs):
        params = {
            'agencyId': '',
            'enteredSearchText': '',
            '_': int(time.time() * 1000),
        }

        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/136.0.0.0 Safari/537.36'
            ),
            'Referer': 'https://bidopportunities.iowa.gov/',
            'X-Requested-With': 'XMLHttpRequest',
        }

        try:
            resp = self.session.get(self.base_url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error: {re}", exc_info=False)
            raise SearchTimeoutError("Iowa search HTTP error") from re

        try:
            data = resp.json()
        except ValueError as ve:
            self.logger.error(f"JSON decode failed: {ve}; response: {resp.text}", exc_info=False)
            raise DataExtractionError("Iowa JSON decode failed") from ve

        return data


    # requires: response_json is a dict containing 'aaData'
    # effects: transforms response_json into list of record dicts
    def extract_data(self, response_json):
        if not response_json or 'aaData' not in response_json:
            self.logger.error("No 'aaData' found in response_json")
            raise DataExtractionError("Iowa extract_data missing 'aaData'")

        raw_records = []
        for entry in response_json['aaData']:
            try:
                code = entry.get('BidNumber', '').strip()
                title = entry.get('Solicitation', '').strip()
                raw_date = entry.get('ExpirationDate', '').strip()
                end_str = ''
                if raw_date:
                    m = re.search(r'/Date\((\d+)\)/', raw_date)
                    if m:
                        ms = int(m.group(1))
                        dt_central = datetime.datetime.fromtimestamp(ms/1000, tz=ZoneInfo("America/Chicago"))
                        central_str = dt_central.strftime("%Y-%m-%d %H:%M:%S")
                        end_str = parse_date_generic(central_str)

                bid_id = entry.get('ID', '').strip()
                base_link = "https://bidopportunities.iowa.gov/Home/BidInfo"
                link = f"{base_link}?bidId={bid_id}" if bid_id else ""

                raw_records.append({
                    'title': title,
                    'code': code,
                    'end_date': end_str,
                    'link': link,
                })
            except Exception as e:
                self.logger.error(f"extract_data entry parsing failed: {e}", exc_info=True)
                continue

        return raw_records


    # effects: orchestrates search -> extract_data -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Iowa")
        try:
            response_json = self.search(**kwargs)
            raw_records = self.extract_data(response_json)
            df = pd.DataFrame(raw_records)
            self.logger.info("Applying filters")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Found {len(filtered)} records after filtering")
            return filtered.to_dict("records")

        except (SearchTimeoutError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"Iowa scrape failed: {e}", exc_info=True)
            raise ScraperError("Iowa scrape failed") from e
