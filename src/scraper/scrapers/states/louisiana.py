# louisiana.py
# url: https://prd.co.cgiadvantage.com/PRDVSS1X1/Advantage4

import logging
import re
import requests
import pandas as pd
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from src.config import STATE_RFP_URL_MAP

from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Louisiana RFP data using Requests
class LouisianaScraper(RequestsScraper):

    # modifies: self
    # effects: initializes the scraper with Louisiana's RFP URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("louisiana"))
        self.logger = logging.getLogger(__name__)


    # effects: issues a GET to fetch the Louisiana RFP page; returns raw HTML or raises on failure
    def search(self, **kwargs):
        self.logger.info("Fetching Louisiana RFP page")
        try:
            resp = self.session.get(self.base_url, timeout=60)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error: {re}", exc_info=False)
            raise SearchTimeoutError("Louisiana search HTTP error") from re
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("Louisiana search failed") from e


    # requires: html is a string of page source
    # effects: parses the <table class='bid'>, handles addenda, extracts structured records
    def extract_data(self, html):
        if not html:
            self.logger.error("No HTML provided to extract_data")
            raise DataExtractionError("Empty HTML for Louisiana extract_data")

        try:
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", class_="bid")
            if not table:
                self.logger.error("<table class='bid'> not found in HTML")
                raise DataExtractionError("Louisiana bid table not found")

            records = []
            last_code = None
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue

                desc_cell = cells[1]
                desc = desc_cell.get_text(separator=" ", strip=True)

                if "Addendum" in desc:
                    code = last_code
                    title = desc
                else:
                    code = cells[0].get_text(strip=True)
                    last_code = code
                    title = desc

                end_dt = ""
                for cell in cells[2:4]:
                    txt = cell.get_text(separator=" ", strip=True)
                    if re.search(r"\d{1,2}:\d{2}:\d{2} (AM|PM)", txt):
                        end_dt = txt
                        break

                pdf_link = desc_cell.find('a', href=re.compile(r"\.pdf$"))
                if pdf_link:
                    link = urljoin(self.base_url, pdf_link['href'])
                else:
                    link = STATE_RFP_URL_MAP.get("louisiana")

                records.append({
                    "title": title,
                    "code": code,
                    "end_date": end_dt,
                    "link": link,
                })

            return records
        except DataExtractionError:
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Louisiana extract_data failed") from e


    # effects: orchestrates search -> extract_data -> filtering; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Louisiana")
        try:
            html = self.search(**kwargs)
            raw_records = self.extract_data(html)

            df = pd.DataFrame(raw_records)
            self.logger.info(f"Total raw records: {len(df)}")

            filtered = filter_by_keywords(df)
            self.logger.info(f"Total after filtering: {len(filtered)}")

            return filtered.to_dict("records")
        except (SearchTimeoutError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"Louisiana scrape failed: {e}", exc_info=True)
            raise ScraperError("Louisiana scrape failed") from e
