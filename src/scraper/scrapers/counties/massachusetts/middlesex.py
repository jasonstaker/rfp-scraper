# middlesex.py
# url: https://procurement.opengov.com/portal/cambridgema

import logging
import requests
import pandas as pd

from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from src.config import COUNTY_RFP_URL_MAP

from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Middlesex County RFP data using Requests and the OpenGov API
class MiddlesexScraper(RequestsScraper):

    # modifies: self
    # effects: initializes the scraper with the Middlesex base URL and sets up logging and headers
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP['massachusetts']['middlesex'])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "Accept":         "application/json",
            "Content-Type":   "application/json",
            "Origin":         "https://procurement.opengov.com",
            "Referer":        "https://procurement.opengov.com/",
            "User-Agent":     "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                                 " AppleWebKit/537.36 (KHTML, like Gecko)"
                                 " Chrome/138.0.0.0 Safari/537.36",
        })


    # effects: issues a POST to the OpenGov API endpoint with pagination; returns raw JSON dict or raises
    def search(self, page: int = 1, limit: int = 200, **kwargs) -> dict:
        payload = {
            "filters":          [{"type": "status", "value": "open"}],
            "quickSearchQuery": None,
            "limit":            limit,
            "page":             page,
        }

        try:
            resp = self.session.post(self.base_url, json=payload, timeout=15)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"search HTTP error (page={page}): {e}")
            raise SearchTimeoutError(f"Middlesex search HTTP error on page {page}") from e

        try:
            data = resp.json()
        except ValueError as e:
            self.logger.error(f"JSON decode failed (page={page}): {e}")
            raise DataExtractionError(f"Middlesex JSON decode failed on page {page}") from e

        if not isinstance(data, dict) or "rows" not in data:
            self.logger.error(f"Unexpected JSON shape: {data}")
            raise DataExtractionError(f"Middlesex search returned invalid JSON on page {page}")

        return data


    # requires: data is a dict containing a 'rows' list
    # effects: transforms API JSON rows into standardized record dicts
    def extract_data(self, data: dict) -> list[dict]:
        rows = data.get("rows", [])
        records = []

        for item in rows:
            try:
                title      = item.get("title", "").strip()
                code       = item.get("financialId") or str(item.get("id", ""))
                end_date   = item.get("proposalDeadline", "").strip()
                link       = f"https://procurement.opengov.com/portal/cambridgema/projects/{item['id']}"

                records.append({
                    "title":    title,
                    "code":     code,
                    "end_date": end_date,
                    "link":     link,
                })
            except Exception as e:
                self.logger.warning(f"Failed to parse row {item.get('id')}: {e}")
                continue

        return records


    # effects: orchestrates search -> extract_data -> filter; returns filtered list of record dicts or raises
    def scrape(self, **kwargs) -> list[dict]:
        self.logger.info("Starting scrape for Middlesex")
        all_recs = []
        page     = 1

        try:
            while True:
                self.logger.info(f"Fetching Middlesex page {page}")
                data  = self.search(page=page, **kwargs)
                recs  = self.extract_data(data)
                if not recs:
                    self.logger.info(f"No more rows on page {page}; stopping")
                    break
                all_recs.extend(recs)
                page += 1

            df      = pd.DataFrame(all_recs)
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except (SearchTimeoutError, DataExtractionError) as e:
            self.logger.error(f"Middlesex scrape failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Middlesex scrape failed: {e}", exc_info=True)
            raise ScraperError("Middlesex scrape failed") from e
