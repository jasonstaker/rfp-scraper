# santa_clara.py
# url: https://api.biddingousa.com/restapi/bidding/list/noauthorize/1/41284411/

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

# a scraper for Santa Clara County solicitations via the BiddingoUSA API
class SantaClaraScraper(RequestsScraper):

    DETAIL_URL = (
        "https://biddingousa.com/santaclaracounty/bid/1/41284411/{tender_id}/verification"
    )

    # modifies: self
    # effects: initializes with API URL and sets up logger & headers
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP["california"]["santa clara"])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json",
        })


    # requires: page (int), limit (int)
    # effects: POSTs to the API for given page & org; returns parsed JSON
    def search(self, page=1, limit=100, **kwargs):
        payload = {
            "startResult": (page - 1) * limit,
            "maxRow": limit,
            "filterRegionId": [],
            "filterCategoryId": [],
            "filterStatus": [],
            "closingDateStart": "",
            "closingDateEnd": "",
            "postedDateStart": "",
            "postedDateEnd": "",
            "selectedRegionId": [],
            "showOnlyResearchBid": False,
            "searchString": "",
            "startDate": "",
            "endDate": "",
            "searchType": "closing",
            "selectedChildOrgIdList": [],
            "sortType": "",
        }
        
        url = self.base_url
        try:
            resp = self.session.post(url, json=payload, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            self.logger.error(f"search HTTP error (page={page}): {e}", exc_info=False)
            raise SearchTimeoutError("SantaClara search HTTP error") from e
        except ValueError as e:
            self.logger.error(f"search JSON decode error: {e}", exc_info=False)
            raise DataExtractionError("SantaClara search JSON decode failed") from e


    # requires: response_json from search()
    # effects: extracts list of {code,title,end_date,link} dicts
    def extract_data(self, data):
        if not data or "bidInfoList" not in data:
            raise DataExtractionError("SantaClara extract_data missing 'bidInfoList'")
        try:
            records = []
            pacific = pytz.timezone("America/Los_Angeles")
            for item in data["bidInfoList"]:
                code = item.get("tenderNumber", "").strip()
                title = item.get("tenderName", "").strip()
                raw_close = item.get("tenderClosingDate", "").strip()
                if raw_close:
                    dt = datetime.strptime(raw_close, "%m/%d/%Y %I:%M:%S %p")
                    dt_local = pacific.localize(dt)
                    end_date = dt_local.strftime("%Y-%m-%d %H:%M %Z")
                else:
                    end_date = ""
                tid = item.get("tenderId")
                link = self.DETAIL_URL.format(tender_id=tid) if tid else ""
                records.append({
                    "code": code,
                    "title": title,
                    "end_date": end_date,
                    "link": link,
                })
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("SantaClara extract_data failed") from e

    # effects: orchestrates pagination -> extract -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Santa Clara County")
        all_records = []
        page = 1
        limit = kwargs.get("limit", 100)

        try:
            while True:
                self.logger.info(f"Fetching page {page}")
                data = self.search(page=page, limit=limit)
                batch = self.extract_data(data)
                if not batch:
                    self.logger.info("No more records; ending pagination")
                    break
                all_records.extend(batch)
                if len(data.get("bidInfoList", [])) < limit:
                    break
                page += 1

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except (SearchTimeoutError, DataExtractionError) as e:
            self.logger.error(f"SantaClara scrape failed: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"SantaClara scrape unexpected error: {e}", exc_info=True)
            raise ScraperError("SantaClara scrape failed") from e
