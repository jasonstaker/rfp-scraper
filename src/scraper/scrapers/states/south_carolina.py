# south_carolina.py
# url: https://scbo.sc.gov/search

import logging
from datetime import datetime
from urllib.parse import urljoin, parse_qs, urlparse

import pandas as pd
from bs4 import BeautifulSoup
import requests
from requests.exceptions import RequestException, SSLError

from scraper.core.requests_scraper import RequestsScraper
from src.config import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for South Carolina RFP data using Requests
class SouthCarolinaScraper(RequestsScraper):

    # modifies: self
    # effects: initializes the scraper with South Carolina Bid Board URL, configures session for HTML
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["south carolina"])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        
        self.session.verify = False
        requests.packages.urllib3.disable_warnings(
            requests.packages.urllib3.exceptions.InsecureRequestWarning
        )


    # effects: POSTs search criteria for current month to December and returns a DataFrame of parsed records
    def search(self, **kwargs):
        now = datetime.now()
        params = {
            'agen': 0,
            'cat': 0,
            'smn': f"{now.month:02d}",
            'syr': now.year,
            'emn': 12,
            'eyr': now.year,
            'submit': 'submit criteria'
        }
        try:
            resp = self.session.post(self.base_url, data=params, timeout=20)
            resp.raise_for_status()
        except SSLError as ssl_err:
            self.logger.warning(f"SSL verification failed, retrying without verify: {ssl_err}")
            try:
                resp = self.session.post(self.base_url, data=params, timeout=20, verify=False)
                resp.raise_for_status()
            except RequestException as re:
                self.logger.error(f"Search HTTP error retry: {re}", exc_info=False)
                raise SearchTimeoutError("South Carolina search HTTP error") from re
            except Exception as e:
                self.logger.error(f"Search retry failed: {e}", exc_info=True)
                raise ScraperError("South Carolina search retry failed") from e
        except RequestException as re:
            self.logger.error(f"Search HTTP error: {re}", exc_info=False)
            raise SearchTimeoutError("South Carolina search HTTP error") from re
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise ScraperError("South Carolina search failed") from e

        try:
            soup = BeautifulSoup(resp.text, 'html.parser')
            rows = soup.find_all('div', class_='pan_rw')
            if not rows or len(rows) <= 1:
                self.logger.error("No result rows found in SCBO search response")
                raise DataExtractionError("South Carolina no result rows")
            records = []
            for row in rows[1:]:
                cols = row.find_all('div', class_='pan_col')
                if len(cols) < 6:
                    continue
                title = cols[0].get_text(strip=True).replace('Title:', '', 1).strip()
                end_date = cols[4].get_text(strip=True).replace('End Date:', '', 1).strip()
                a = cols[5].find('a', href=True)
                href = a['href'] if a else ''
                link = urljoin(self.base_url, href)
                parsed = parse_qs(urlparse(href).query)
                code = parsed.get('s', [''])[0]
                records.append({
                    'title': title,
                    'code': code,
                    'end_date': end_date,
                    'link': link,
                })
            df = pd.DataFrame(records)
            self.logger.info(f"Parsed {len(df)} South Carolina RFP records")
            return df
        except DataExtractionError:
            raise
        except Exception as e:
            self.logger.error(f"Parsing failed: {e}", exc_info=True)
            raise DataExtractionError("South Carolina extract_data failed") from e


    # effects: orchestrates full scrape: search -> filter -> return list of dicts
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for South Carolina")
        try:
            df = self.search(**kwargs)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict('records')
        except (SearchTimeoutError, DataExtractionError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"South Carolina scrape failed: {e}", exc_info=True)
            raise ScraperError("South Carolina scrape failed") from e
