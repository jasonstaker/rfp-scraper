# massachusetts.py
# url: https://www.commbuys.com/bso/view/search/external/advancedSearchBid.xhtml

import logging
import os
import pandas as pd
from bs4 import BeautifulSoup
import requests

from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.config.settings import STATE_RFP_URL_MAP

from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Massachusetts RFP data using Requests
class MassachusettsScraper(RequestsScraper):

    # modifies: self
    # effects: initializes scraper with Commbuys endpoint, sets up logging and session
    def __init__(self):
        super().__init__("https://www.commbuys.com/bso/view/search/external/advancedSearchBid.xhtml?openBids=true")
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.commbuys.com/bso/view/search/external/advancedSearchBid.xhtml?openBids=true",
        })


    # modifies: session cookies and filesystem
    # effects: POSTS form data to trigger CSV download, saves file to temp, reads into DataFrame or raises
    def search(self, **kwargs):
        self.logger.info("Requesting CSV export from Massachusetts Commbuys")
        temp_dir = os.path.join(os.path.dirname(__file__), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, "bidSearchResults.csv")
        try:
            # initial GET to retrieve form tokens
            resp_get = self.session.get(self.base_url, timeout=30)
            resp_get.raise_for_status()
            soup = BeautifulSoup(resp_get.text, "html.parser")
            csrf = soup.find('input', {'name': '_csrf'})['value']
            viewstate = soup.find('input', {'name': 'javax.faces.ViewState'})['value']

            payload = {
                "bidSearchResultsForm": "bidSearchResultsForm",
                "_csrf": csrf,
                "openBids": "true",
                "bidSearchResultsForm:bidResultId_reflowDD": "bidSearchResultsForm:bidResultId:j_idt430_0",
                "javax.faces.ViewState": viewstate,
                "bidSearchResultsForm:bidResultId:j_idt420": "bidSearchResultsForm:bidResultId:j_idt420",
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            resp = self.session.post(self.base_url, data=payload, headers=headers, timeout=60)
            resp.raise_for_status()
        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error: {re}", exc_info=False)
            raise SearchTimeoutError("Massachusetts search HTTP error") from re
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("Massachusetts search failed") from e

        content_disp = resp.headers.get('content-disposition', '')
        if 'attachment' not in content_disp or not resp.content:
            self.logger.error("Did not receive CSV attachment")
            raise DataExtractionError("Massachusetts did not receive CSV")

        try:
            with open(temp_path, "wb") as f:
                f.write(resp.content)
            df = pd.read_csv(temp_path, dtype=str)
            df.columns = [col.strip() for col in df.columns]
            self.logger.info(f"Read {len(df)} rows from CSV")
            return df
        except Exception as e:
            self.logger.error(f"Failed to read CSV: {e}", exc_info=True)
            raise DataExtractionError("Massachusetts CSV read failed") from e


    # requires: df is a pandas DataFrame
    # effects: maps raw CSV columns to standardized records list
    def extract_data(self, df):
        if df is None or df.empty:
            self.logger.warning("Empty DataFrame received for extraction")
            return []
        try:
            output = []
            for _, row in df.iterrows():
                title = row.get("Description", "").strip()
                code = row.get("Bid Solicitation #", "").strip()
                end_date = row.get("Bid Opening Date", "").strip()
                link = STATE_RFP_URL_MAP.get("massachusetts")
                output.append({
                    "title": title,
                    "code": code,
                    "end_date": end_date,
                    "link": link,
                })
            return output
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Massachusetts extract_data failed") from e


    # effects: orchestrates scrape: download CSV -> extract -> filter -> return or raises
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Massachusetts via CSV")
        try:
            df = self.search(**kwargs)
            records = self.extract_data(df)
            df_records = pd.DataFrame(records)
            self.logger.info(f"Total raw records before filtering: {len(df_records)}")
            filtered = filter_by_keywords(df_records)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except (SearchTimeoutError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"Massachusetts scrape failed: {e}", exc_info=True)
            raise ScraperError("Massachusetts scrape failed") from e