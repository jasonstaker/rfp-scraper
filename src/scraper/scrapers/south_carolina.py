# south_carolina.py
# url: https://scbo.sc.gov/search

import logging
from datetime import datetime
from urllib.parse import urljoin, parse_qs, urlparse

import pandas as pd
from bs4 import BeautifulSoup
import requests

from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.config.settings import STATE_RFP_URL_MAP

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
        # disable SSL verification to handle certificate errors
        self.session.verify = False
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

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
        except requests.exceptions.SSLError as ssl_err:
            self.logger.warning(f"SSL verification failed, retrying without verify: {ssl_err}")
            resp = self.session.post(self.base_url, data=params, timeout=20, verify=False)
        except Exception as e:
            self.logger.error(f"Search HTTP error: {e}", exc_info=True)
            raise

        soup = BeautifulSoup(resp.text, 'html.parser')
        rows = soup.find_all('div', class_='pan_rw')
        if not rows or len(rows) <= 1:
            self.logger.error("No result rows found in SCBO search response")
            raise RuntimeError("Parsing error or no results")

        records = []
        for row in rows[1:]:
            try:
                cols = row.find_all('div', class_='pan_col')
                if len(cols) < 6:
                    continue

                label = cols[0].get_text(strip=True).replace('Title:', '', 1).strip()
                # other fields can be extracted similarly if needed
                end_date = cols[4].get_text(strip=True).replace('End Date:', '', 1).strip()

                a = cols[5].find('a', href=True)
                href = a['href'] if a else ''
                link = urljoin(self.base_url, href)
                parsed = parse_qs(urlparse(href).query)
                code = parsed.get('s', [''])[0]

                records.append({
                    'Label': label,
                    'Code': code,
                    'End (UTC-7)': end_date,
                    'Keyword Hits': '',
                    'Link': link,
                })
            except Exception as row_ex:
                self.logger.error(f"Failed processing SCBO row: {row_ex}")
                continue

        df = pd.DataFrame(records)
        self.logger.info(f"Parsed {len(df)} South Carolina RFP records")
        return df

    # effects: orchestrates full scrape: search -> filter -> return list of dicts
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for South Carolina")
        try:
            df = self.search(**kwargs)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict('records')
        except Exception as e:
            self.logger.error(f"South Carolina scrape failed: {e}", exc_info=True)
            raise
