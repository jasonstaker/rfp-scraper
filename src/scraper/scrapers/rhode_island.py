# rhode_island.py
# url: https://ridop.ri.gov/vendors/bidding-opportunities

import logging
from datetime import datetime
import pytz

import pandas as pd
import requests

from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.config.settings import STATE_RFP_URL_MAP

# a scraper for Rhode Island RFP data using Requests
class RhodeIslandScraper(RequestsScraper):
    # modifies: self
    # effects: initializes the scraper with Rhode Island's Proactis JSON endpoint, sets headers
    def __init__(self):
        base = "https://webprocure.proactiscloud.com/wp-full-text-search/search/sols"
        super().__init__(base)
        self.logger = logging.getLogger(__name__)
        # expect JSON
        self.session.headers.update({
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        })

    # effects: fetches a JSON page at given offset for customerid=46, returns JSON dict
    def _fetch_page(self, offset: int):
        params = {
            "customerid": 46,
            "q": "*",
            "from": offset,
            "sort": "r",
            "f": "ps=Open",
            "oids": "",
        }
        try:
            resp = self.session.get(self.base_url, params=params, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as e:
            self.logger.error(f"HTTP request failed (offset={offset}): {e}", exc_info=False)
            raise

        if "application/json" not in resp.headers.get("Content-Type", "").lower():
            snippet = resp.text[:200].replace("\n", " ")
            self.logger.error(f"Expected JSON but got: {snippet!r}")
            raise RuntimeError("Non-JSON response")

        try:
            return resp.json()
        except ValueError as e:
            snippet = resp.text[:200].replace("\n", " ")
            self.logger.error(f"JSON parse error: {e}; snippet: {snippet!r}", exc_info=False)
            raise

    # effects: retrieves total_hits, page_size, and first_page JSON via _fetch_page
    def search(self, **kwargs):
        self.logger.info("Fetching first page of Rhode Island solicitations...")
        first_page = self._fetch_page(offset=0)
        total_hits = first_page.get("hits", 0)
        page_size = len(first_page.get("records", []))
        self.logger.info(f"total_hits={total_hits}, page_size={page_size}")
        return total_hits, page_size, first_page

    # requires: page_content is JSON dict with "records"
    # effects: extracts standardized records list from JSON page_content
    def extract_data(self, page_content: dict):
        if not page_content or "records" not in page_content:
            self.logger.error('No page_content or missing "records"')
            raise RuntimeError("Invalid JSON content")

        records = []
        pacific = pytz.timezone("US/Pacific")
        for rec in page_content["records"]:
            try:
                title = rec.get("title", "").strip()
                code = rec.get("bidNumber", "").strip()
                
                ts = rec.get("openDate") or rec.get("statusDate")
                if ts:
                    dt_utc = datetime.fromtimestamp(ts/1000, tz=pytz.UTC)
                    dt_pst = dt_utc.astimezone(pacific)
                    end_str = dt_pst.strftime("%Y-%m-%d %H:%M:%S %Z")
                else:
                    end_str = ""
                link = STATE_RFP_URL_MAP.get('rhode_island', self.base_url)

                records.append({
                    "title": title,
                    "code": code,
                    "end_date": end_str,
                    "link": link,
                })
            except Exception as e:
                self.logger.error(f"Error parsing record: {e}")
                continue
        return records

    # effects: orchestrates search -> paginate -> extract -> filter -> return dicts
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Rhode Island")
        all_records = []
        total_hits, page_size, first_page = self.search(**kwargs)
        
        batch = self.extract_data(first_page)
        all_records.extend(batch)

        offset = page_size
        page = 2
        while offset < total_hits:
            self.logger.info(f"Fetching page {page} (offset={offset})...")
            page_json = self._fetch_page(offset=offset)
            batch = self.extract_data(page_json)
            all_records.extend(batch)
            offset += page_size
            page += 1

        df = pd.DataFrame(all_records)
        self.logger.info(f"Total raw records: {len(df)}")
        filtered = filter_by_keywords(df)
        self.logger.info(f"Records after filtering: {len(filtered)}")
        return filtered.to_dict("records")
