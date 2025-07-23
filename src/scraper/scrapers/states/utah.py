# utah.py
# url: https://utah.bonfirehub.com/portal/?tab=openOpportunities

import logging
import time
import pandas as pd
import requests
from requests.exceptions import RequestException, JSONDecodeError

from scraper.core.requests_scraper import RequestsScraper
from src.config import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Utah RFP data using Requests
class UtahScraper(RequestsScraper):

    # modifies: self
    # effects: initializes scraper with Utah Bonfire public portal URL and sets headers
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP['utah'])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            'Accept':           'application/json, text/javascript, */*; q=0.01',
            'User-Agent':       (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/137.0.0.0 Safari/137.0.0.0'
            ),
            'X-Requested-With': 'XMLHttpRequest',
            'Referer':          'https://utah.bonfirehub.com/'
        })


    # effects: issues a GET to fetch the JSON of open projects
    def search(self, **kwargs):
        timestamp = int(time.time() * 1000)
        url = f"{self.base_url}?_={timestamp}"
        try:
            self.logger.info("Fetching Utah RFP JSON payload")
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except RequestException as re:
            self.logger.error(f"search HTTP error: {re}", exc_info=False)
            raise SearchTimeoutError("Utah search HTTP error") from re
        except JSONDecodeError as je:
            self.logger.error(f"search JSON decode failed: {je}", exc_info=False)
            raise DataExtractionError("Utah search JSON decode failed") from je
        except Exception as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            raise ScraperError("Utah search failed") from e


    # requires: response_json from search()
    # effects: parses projects dict into a list of record dicts
    def extract_data(self, response_json):
        payload = response_json.get('payload', {})
        projects = payload.get('projects', {})
        if not isinstance(projects, dict) or not projects:
            self.logger.error("No 'projects' found in Utah JSON payload")
            raise DataExtractionError("Utah extract_data missing 'projects'")

        records = []
        try:
            for proj in projects.values():
                project_id = proj.get('ProjectID', '').strip()
                code = proj.get('ReferenceID', '').strip()
                title = proj.get('ProjectName', '').strip()

                raw_date = proj.get('DateClose', '').strip()
                end_str = parse_date_generic(raw_date) if raw_date else ''

                link = f"https://utah.bonfirehub.com/opportunities/{project_id}" if project_id else self.base_url

                records.append({
                    'title': title,
                    'code': code,
                    'end_date': end_str,
                    'link': link,
                })
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Utah extract_data failed") from e


    # effects: runs search -> extract_data -> DataFrame -> filter_by_keywords -> return records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Utah")
        try:
            data = self.search(**kwargs)
            raw_records = self.extract_data(data)

            df = pd.DataFrame(raw_records)
            self.logger.info(f"Total raw records: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total after filtering: {len(filtered)}")
            return filtered.to_dict('records')
        except (SearchTimeoutError, DataExtractionError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"Utah scrape failed: {e}", exc_info=True)
            raise ScraperError("Utah scrape failed") from e
