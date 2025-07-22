# new_mexico.py
# url: https://bids.sciquest.com/apps/Router/PublicEvent?CustomerOrg=StateOfNewMexico&tab=PHX_NAV_SourcingOpenForBid

import logging
import time
import re

import pandas as pd
from bs4 import BeautifulSoup

from scraper.core.requests_scraper import RequestsScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic

# a scraper for New Mexico RFP data using Requests
class NewMexicoScraper(RequestsScraper):
    # modifies: self
    # effects: initializes the scraper with New Mexico's PublicEvent URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get('new mexico'))
        self.logger = logging.getLogger(__name__)

    # effects: requests the SciQuest PublicEvent page with a current timestamp and returns the HTML
    def search(self, **kwargs):
        ts = int(time.time() * 1000)
        url = f"{self.base_url}{ts}"
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/137.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://bids.sciquest.com/',
        }

        try:
            self.logger.info(f"Fetching New Mexico events page (ts={ts})")
            resp = self.session.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                self.logger.error(f"search HTTP status {resp.status_code}: {resp.text!r}")
                resp.raise_for_status()
            return resp.text
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise

    # requires: HTML text of the events page
    # effects: parses the Open events table and returns a list of raw record dicts
    def extract_data(self, html):
        if not html:
            self.logger.error("No HTML provided to extract_data")
            raise RuntimeError("No HTML provided")

        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='table phx table-hover no-column-borders')
        if not table:
            self.logger.error("Results table not found")
            raise RuntimeError("Could not find events table")

        rows = table.find_all('tr')
        body_rows = rows[1:]

        records = []
        for row in body_rows:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            details_td = cols[1]
            link_a = details_td.select_one("a.btn.btn-link")
            if not link_a:
                continue
            title = link_a.get_text(strip=True)
            link  = link_a["href"]

            data_rows = details_td.select("div.phx.table-row-layout")

            def _find_value(suffix, strip_tz=False):
                for dr in data_rows:
                    id_div = dr.find("div", id=lambda i: i and suffix in i)
                    if id_div:
                        content = dr.select_one("div.phx.data-row-content")
                        if content:
                            text = content.get_text(strip=True)
                            if strip_tz:
                                # only strip trailing timezone token
                                return text.rsplit(" ", 1)[0]
                            return text
                return ""

            # only remove timezone from the Close date
            end_str = _find_value("LABEL_CLOSE")
            code    = _find_value("LABEL_NUMBER")

            records.append({
                "title":        title,
                "code":         code,
                "end_date":  end_str,
                "link":         link,
            })

        return records

    # effects: orchestrates full scrape: search -> extract_data -> filtering; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for New Mexico")
        try:
            html = self.search(**kwargs)
            raw = self.extract_data(html)

            df = pd.DataFrame(raw)
            self.logger.info(f"Total raw records: {len(df)}")

            filtered = filter_by_keywords(df)
            self.logger.info(f"Total after filtering: {len(filtered)}")

            return filtered.to_dict('records')
        except Exception as e:
            self.logger.error(f"New Mexico scrape failed: {e}", exc_info=True)
            raise
