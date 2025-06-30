# nebraska.py
# url: https://das.nebraska.gov/materiel/bid-opportunities.html

import logging
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.config.settings import STATE_RFP_URL_MAP

# a scraper for Nebraska RFP data using Requests
class NebraskaScraper(RequestsScraper):
    # effects: initialize with base URL and logger
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["nebraska"])
        self.logger = logging.getLogger(__name__)

    # effects: GET page and parse HTML table into DataFrame
    def search(self, **kwargs):
        self.logger.info("Fetching Nebraska bid opportunities page")
        resp = self.session.get(self.base_url, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="table table-bordered table-striped table-responsive")
        if not table:
            self.logger.error("Bids table not found on Nebraska page")
            raise RuntimeError("Bids table missing")

        tbody = table.find("tbody") or table
        records = []
        for row in tbody.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 8:
                continue
            # Description link and label
            a = cols[1].find("a", href=True)
            label = a.get_text(strip=True) if a else cols[1].get_text(strip=True)
            link = urljoin(self.base_url, a["href"]) if a else self.base_url
            # Solicitation Number
            code = cols[6].get_text(strip=True)
            # Opening date as end date
            end_date = cols[3].get_text(strip=True)

            records.append({
                "Label": label,
                "Code": code,
                "End (UTC-7)": end_date,
                "Keyword Hits": "",
                "Link": link,
            })

        df = pd.DataFrame(records)
        self.logger.info(f"Parsed {len(df)} records from Nebraska bids table")
        return df

    # effects: wrap search + filter and return list of dicts
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Nebraska")
        df = self.search(**kwargs)
        self.logger.info(f"Total raw records before filtering: {len(df)}")
        filtered = filter_by_keywords(df)
        self.logger.info(f"Total records after filtering: {len(filtered)}")
        return filtered.to_dict("records")
