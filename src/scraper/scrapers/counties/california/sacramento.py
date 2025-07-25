# sacramento.py
# url: https://api.procurement.opengov.com/api/v1/government/ocgov/project/public

import logging
import pandas as pd
import requests
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

# a scraper for Sacramento County solicitations via the OpenGov API
class SacramentoScraper(RequestsScraper):

    DETAIL_URL = "https://procurement.opengov.com/portal/saccounty/projects/{id}"

    # modifies: self
    # effects: initializes with API URL and sets up logger & JSON headers
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP["california"]["sacramento"])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept":       "application/json",
        })


    # requires: page (int), limit (int)
    # modifies: none
    # effects: POSTs to the API with filters for open status, pagination, sorting; returns parsed JSON
    def search(self, page=1, limit=100, **kwargs):
        payload = {
            "filters":         [{"type": "status", "value": "open"}],
            "quickSearchQuery": None,
            "limit":           limit,
            "page":            page,
            "sortField":       "proposalDeadline",
            "sortDirection":   "ASC",
        }
        try:
            resp = self.session.post(self.base_url, json=payload, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            self.logger.error(f"search HTTP error (page={page}): {e}", exc_info=False)
            raise SearchTimeoutError("Sacramento search HTTP error") from e
        except ValueError as e:
            self.logger.error(f"search JSON decode error: {e}", exc_info=False)
            raise DataExtractionError("Sacramento search JSON decode failed") from e


    # requires: response_json from search()
    # effects: extracts list of {title, code, end_date, link} dicts
    def extract_data(self, response_json):
        if not response_json or "rows" not in response_json:
            raise DataExtractionError("Sacramento extract_data missing 'rows'")
        try:
            records = []
            
            pacific = pytz.timezone("America/Los_Angeles")
            for proj in response_json["rows"]:
                code = proj.get("financialId", "").strip()
                title = proj.get("title", "").strip()
                
                dl_iso = proj.get("proposalDeadline")
                if dl_iso:
                    dt_utc = datetime.fromisoformat(dl_iso.replace("Z", "+00:00"))
                    dt_local = dt_utc.astimezone(pacific)
                    end_date = dt_local.strftime("%Y-%m-%d %H:%M %Z")
                else:
                    end_date = ""
                
                pid = proj.get("id")
                link = self.DETAIL_URL.format(id=pid) if pid else ""
                records.append({
                    "code":     code,
                    "title":    title,
                    "end_date": end_date,
                    "link":     link,
                })
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Sacramento extract_data failed") from e


    # effects: orchestrates pagination -> extract -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Sacramento County")
        all_records = []
        page  = 1
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
                
                if len(data.get("rows", [])) < limit:
                    break
                page += 1

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except (SearchTimeoutError, DataExtractionError) as e:
            self.logger.error(f"Sacramento scrape failed: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Sacramento scrape unexpected error: {e}", exc_info=True)
            raise ScraperError("Sacramento scrape failed") from e
