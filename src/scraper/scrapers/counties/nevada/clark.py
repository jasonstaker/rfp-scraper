# clark.py
# url: https://www.demandstar.com/app/agencies/nevada/clark-county-nv/procurement-opportunities/e43ae9f5-b03b-400b-87ba-874dedef1951/

import logging
import requests
import pandas as pd
from datetime import datetime
import pytz

from src.config import COUNTY_RFP_URL_MAP
from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Clark County, NV solicitations via the DemandStar API
class ClarkScraper(RequestsScraper):

    # effects: initializes with DemandStar Clark County search URL and sets up logger & headers
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP["nevada"]["clark"])
        self.logger = logging.getLogger(__name__)
        
        self.session.headers.update({
            "Accept": "application/json"
        })
        self.session.headers.pop("Content-Type", None)


    # effects: GETs the API for Clark County bids; returns parsed JSON
    def search(self, **kwargs):
        try:
            resp = self.session.get(self.base_url, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            self.logger.error(f"search HTTP error: {e}", exc_info=False)
            raise SearchTimeoutError("Clark search HTTP error") from e
        except ValueError as e:
            self.logger.error(f"search JSON decode error: {e}", exc_info=False)
            raise DataExtractionError("Clark search JSON decode failed") from e


    # requires: response_json from search()
    # effects: extracts list of active bids as {code, title, end_date, link} dicts
    def extract_data(self, data):
        if not data or "result" not in data:
            raise DataExtractionError("Clark extract_data missing 'result'")
        try:
            records = []
            pacific = pytz.timezone("America/Los_Angeles")
            for item in data["result"]:
                if item.get("status") != "Active":
                    continue
                code = item.get("bidIdentifier", "").strip()
                title = item.get("bidName", "").strip()
                raw_due = item.get("dueDate", "").strip()
                if raw_due:
                    dt = datetime.strptime(raw_due, "%m/%d/%Y")
                    dt_local = pacific.localize(dt)
                    end_date = dt_local.strftime("%Y-%m-%d %H:%M %Z")
                else:
                    end_date = ""
                
                bid_id = item.get("bidId")
                link = f"https://www.demandstar.com/app/limited/bids/{bid_id}/details" if bid_id else ""

                records.append({
                    "code": code,
                    "title": title,
                    "end_date": end_date,
                    "link": link,
                })
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Clark extract_data failed") from e


    # effects: orchestrates search -> extract_data -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Clark County, NV")
        try:
            data = self.search()
            raw = self.extract_data(data)
            df = pd.DataFrame(raw)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except (SearchTimeoutError, DataExtractionError) as e:
            self.logger.error(f"Clark scrape failed: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Clark scrape unexpected error: {e}", exc_info=True)
            raise ScraperError("Clark scrape failed") from e