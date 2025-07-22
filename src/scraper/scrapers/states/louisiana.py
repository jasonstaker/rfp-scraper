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
from scraper.config.settings import STATE_RFP_URL_MAP

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
            if resp.status_code != 200:
                self.logger.error(f"search HTTP status {resp.status_code}: {resp.text!r}")
                resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error: {re}", exc_info=False)
            raise
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise

    # requires: html is a string of page source
    # effects: parses the <table class='bid'>, handles addenda, extracts structured records
    def extract_data(self, html):
        if not html:
            self.logger.error("No HTML provided to extract_data")
            raise RuntimeError("No HTML provided")

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", class_="bid")
        if not table:
            self.logger.error("<table class='bid'> not found in HTML")
            raise RuntimeError("Could not find bid table")

        records = []
        last_code = None

        for row in table.find_all("tr")[1:]:  # skip header row
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            desc_cell = cells[1]
            desc = desc_cell.get_text(separator=" ", strip=True)

            # Determine if row is an addendum
            if "Addendum" in desc:
                code = last_code
                title = desc
            else:
                code = cells[0].get_text(strip=True)
                last_code = code
                title = desc

            # Extract end datetime by AM/PM pattern
            end_dt = ""
            for cell in cells[2:4]:
                txt = cell.get_text(separator=" ", strip=True)
                if re.search(r"\d{1,2}:\d{2}:\d{2} (AM|PM)", txt):
                    end_dt = txt
                    break

            # Extract PDF link from description; fallback to base URL
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

    # effects: orchestrates search -> extract_data -> filtering; returns filtered records or raises on failure
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
        except Exception as e:
            self.logger.error(f"Scrape failed: {e}", exc_info=True)
            raise
