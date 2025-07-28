# broward.py
# url: https://broward.bonfirehub.com/PublicPortal/getOpenPublicOpportunitiesSectionData?=_

import logging
import requests
import pandas as pd
from datetime import datetime
import pytz
import time

from src.config import COUNTY_RFP_URL_MAP
from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Broward County solicitations via the BonfireHub PublicPortal API
class BrowardScraper(RequestsScraper):

    DETAIL_URL = "https://broward.bonfirehub.com/opportunities/{id}"

    # modifies: self
    # effects: initializes with API URL and sets up logger & headers
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP["florida"]["broward"])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        })


    # effects: GETs the API with a millisecond timestamp to bypass cache; returns parsed JSON
    def search(self, **kwargs):
        timestamp = str(int(time.time() * 1000))
        url = f"{self.base_url}{timestamp}"
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            self.logger.error(f"search HTTP error: {e}", exc_info=False)
            raise SearchTimeoutError("Broward search HTTP error") from e
        except ValueError as e:
            self.logger.error(f"search JSON decode error: {e}", exc_info=False)
            raise DataExtractionError("Broward search JSON decode failed") from e



    # requires: response_json from search()
    # effects: extracts list of {code, title, end_date, link} dicts
    def extract_data(self, data):
        if not data or "payload" not in data or "projects" not in data["payload"]:
            raise DataExtractionError("Broward extract_data missing 'payload.projects'")
        try:
            records = []
            eastern = pytz.timezone("America/New_York")
            for pid, proj in data["payload"]["projects"].items():
                code = proj.get("ReferenceID", "").strip()
                title = proj.get("ProjectName", "").strip()
                raw_close = proj.get("DateClose", "").strip()
                if raw_close:
                    dt = datetime.strptime(raw_close, "%Y-%m-%d %H:%M:%S")
                    dt_local = eastern.localize(dt)
                    
                    end_date = dt_local.strftime("%B %d, %Y")
                else:
                    end_date = ""
                link = self.DETAIL_URL.format(id=pid)
                records.append({
                    "code": code,
                    "title": title,
                    "end_date": end_date,
                    "link": link,
                })
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Broward extract_data failed") from e


    # effects: orchestrates single-fetch -> extract -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Broward County")
        try:
            data = self.search()
            raw = self.extract_data(data)
            df = pd.DataFrame(raw)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except (SearchTimeoutError, DataExtractionError) as e:
            self.logger.error(f"Broward scrape failed: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Broward scrape unexpected error: {e}", exc_info=True)
            raise ScraperError("Broward scrape failed") from e