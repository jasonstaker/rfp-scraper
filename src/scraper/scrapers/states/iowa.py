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
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic

# a scraper for Iowa RFP data using Requests
class IowaScraper(RequestsScraper):
    # modifies: self
    # effects: initializes the scraper with Iowa's hosted bids search URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP['iowa'])
        self.logger = logging.getLogger(__name__)

    # effects: issues a GET to the Iowa hosted bids search endpoint with the required query parameters and headers
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
            if resp.status_code != 200:
                self.logger.error(f"GET failed: {resp.status_code} -> {resp.text}")
                raise

            data = resp.json()
            return data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"search HTTP error: {e}", exc_info=False)
            raise
        except ValueError as ve:
            self.logger.error(f"JSON decode failed: {ve}; response: {resp.text}", exc_info=False)
            raise
        except Exception as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            raise

    # requires: response_json is a dict or None
    # effects: transforms response_json into a list of dicts with keys
    def extract_data(self, response_json):
        if not response_json or 'aaData' not in response_json:
            self.logger.error("No 'aaData' found in response_json")
            raise

        raw_records = []
        for entry in response_json['aaData']:
            try:
                code = entry.get('BidNumber', '').strip()

                title = entry.get('Solicitation', '').strip()

                raw_date = entry.get('ExpirationDate', '').strip()
                if raw_date:
                    # Extract the millisecond timestamp
                    m = re.search(r'/Date\((\d+)\)/', raw_date)
                    if m:
                        ms_since_epoch = int(m.group(1))
                        dt_central = datetime.datetime.fromtimestamp(ms_since_epoch / 1000.0, tz=ZoneInfo("America/Chicago"))
                        central_str = dt_central.strftime("%Y-%m-%d %H:%M:%S")
                        end_str = parse_date_generic(central_str)
                    else:
                        end_str = ""
                else:
                    end_str = ""

                # build the bid detail link:
                #    https://bidopportunities.iowa.gov/Home/BidInfo?bidId=<ID>
                bid_id = entry.get('ID', '').strip()
                base_link = "https://bidopportunities.iowa.gov/Home/BidInfo"
                link = f"{base_link}?bidId={bid_id}" if bid_id else ""

                raw_records.append({
                    "title": title,
                    "code": code,
                    "end_date": end_str,
                    "link": link,
                })

            except Exception as e:
                self.logger.error(f"extract_data entry parsing failed: {e}", exc_info=True)
                continue

        return raw_records

    # effects: orchestrates search -> extract_data -> filter_by_keywords; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Iowa")
        try:
            response_json = self.search(**kwargs)
            if response_json is None:
                self.logger.warning("search returned no data; aborting scrape")
                raise

            self.logger.info("Processing JSON data")
            raw_records = self.extract_data(response_json)

            # convert to DataFrame, apply filter_by_keywords, return list of dicts
            df = pd.DataFrame(raw_records)
            self.logger.info("Applying keyword filters")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Found {len(filtered)} records after filtering")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"Iowa scrape failed: {e}", exc_info=True)
            raise
