# franklin.py
# url: https://www.franklincountyohio.gov/Business-Development/Do-Business-With-Us/Bids-Purchasing

import logging
from urllib.parse import urljoin
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

from src.config import COUNTY_RFP_URL_MAP
from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Franklin County, OH bid opportunities via HTML table
class FranklinScraper(RequestsScraper):

    # effects: initializes with Franklin County bids URL and logger
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP["ohio"]["franklin"])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })


    # effects: GETs the bids table page; returns HTML text
    def search(self, **kwargs):
        try:
            resp = self.session.get(self.base_url, timeout=20)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            self.logger.error(f"search HTTP error: {e}", exc_info=False)
            raise SearchTimeoutError("Franklin search HTTP error") from e


    # requires: HTML string from search()
    # effects: parses the sticky table rows into records list
    def extract_data(self, html):
        try:
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", class_="sticky table table-striped mobile")
            if not table:
                raise DataExtractionError("Franklin table not found")
            rows = table.find_all("tr")[1:]

            records = []
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue
                
                code = cols[0].get_text(strip=True)
                
                link_tag = cols[1].find("a", href=True)
                title = link_tag.get_text(strip=True) if link_tag else ""
                href = link_tag["href"] if link_tag else ""
                link = urljoin(self.base_url, href)
                
                raw_date = cols[2].get_text(strip=True)
                try:
                    dt = datetime.strptime(raw_date, "%m/%d/%Y")
                    end_date = dt.strftime("%Y-%m-%d")
                except ValueError:
                    end_date = raw_date

                records.append({
                    "code": code,
                    "title": title,
                    "end_date": end_date,
                    "link": link,
                })
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Franklin extract_data failed") from e


    # effects: orchestrates search -> extract_data -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Franklin County, OH")
        try:
            html = self.search()
            raw = self.extract_data(html)
            df = pd.DataFrame(raw)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except (SearchTimeoutError, DataExtractionError) as e:
            self.logger.error(f"Franklin scrape failed: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Franklin scrape unexpected error: {e}", exc_info=True)
            raise ScraperError("Franklin scrape failed") from e
