# south_dakota.py
# url: https://postingboard.esmsolutions.com/3444a404-3818-494f-84c5-2a850acd7779/events

import logging
from datetime import datetime
from urllib.parse import urljoin

import pandas as pd
import requests
from requests.exceptions import RequestException

from scraper.core.requests_scraper import RequestsScraper
from src.config import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for South Dakota RFP data using Requests
class SouthDakotaScraper(RequestsScraper):

    # modifies: self
    # effects: initializes scraper with SD posting board API URL and configures session
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["south dakota"])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*"
        })


    # effects: fetches all events in one request by using a large recordsPerPage
    def search(self, **kwargs):
        params = {
            "pageNo": 0,
            "recordsPerPage": kwargs.get("recordsPerPage", 1000),
            "browserGlobalTimeZoneNameId": "Pacific Daylight Time",
            "browserGlobalTimeZoneName": "America/Los_Angeles",
            "browserOffset": "-07:00:00",
        }
        try:
            resp = self.session.get(self.base_url, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except RequestException as re:
            self.logger.error(f"Search HTTP error: {re}", exc_info=False)
            raise SearchTimeoutError("South Dakota search HTTP error") from re
        except ValueError as ve:
            self.logger.error(f"JSON decode error: {ve}", exc_info=False)
            raise DataExtractionError("South Dakota JSON decode failed") from ve
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise ScraperError("South Dakota search failed") from e


    # requires: response_json is dict with 'data'
    # effects: extracts event records into standardized list of dicts
    def extract_data(self, response_json):
        if not response_json or "data" not in response_json:
            self.logger.error("Invalid JSON content in extract_data")
            raise DataExtractionError("South Dakota extract_data missing 'data'")

        try:
            board_id = '3444a404-3818-494f-84c5-2a850acd7779'
            base_detail = f"https://postingboard.esmsolutions.com/{board_id}/eventDetail/"

            records = []
            for rec in response_json["data"]:
                title = rec.get("eventName", "").strip()
                code = rec.get("id", "").strip()

                end_str = rec.get("eventDueDate", "").strip()
                try:
                    dt = datetime.fromisoformat(end_str)
                    end_fmt = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    end_fmt = end_str

                event_id = rec.get("eventId", "").strip()
                link = urljoin(base_detail, event_id)

                records.append({
                    "title": title,
                    "code": code,
                    "end_date": end_fmt,
                    "link": link,
                })

            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("South Dakota extract_data failed") from e


    # effects: orchestrates full scrape: search -> extract_data -> filter -> return
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for South Dakota")
        try:
            response_json = self.search(**kwargs)
            raw_records = self.extract_data(response_json)

            df = pd.DataFrame(raw_records)
            self.logger.info(f"Total raw records: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except (SearchTimeoutError, DataExtractionError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"South Dakota scrape failed: {e}", exc_info=True)
            raise ScraperError("South Dakota scrape failed") from e
