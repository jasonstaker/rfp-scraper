# minnesota.py
# url: https://osp.admin.mn.gov/GS-auto

import logging
from datetime import datetime
import pandas as pd
import pytz
from bs4 import BeautifulSoup

from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from src.config import STATE_RFP_URL_MAP

from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Minnesota RFP data using Requests
class MinnesotaScraper(RequestsScraper):

    # modifies: self
    # effects: initializes the scraper with Minnesota’s RFP URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("minnesota"))
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })


    # effects: GETs the main page and returns a BeautifulSoup object or raises
    def _fetch_page(self):
        self.logger.info("Fetching Minnesota RFP HTML page")
        try:
            resp = self.session.get(self.base_url, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            self.logger.error(f"search HTTP error: {e}", exc_info=False)
            raise SearchTimeoutError("Minnesota search HTTP error") from e


    # requires: soup is a BeautifulSoup object
    # effects: parses the UL/LI structure into a DataFrame or raises
    def extract_data(self, soup: BeautifulSoup):
        try:
            container = soup.find("div", class_="item-list")
            if not container:
                self.logger.error('<div class="item-list"> not found')
                raise DataExtractionError("Minnesota RFP container missing")

            ul = container.find("ul")
            if not ul:
                self.logger.error("<ul> not found inside .item-list")
                raise DataExtractionError("Minnesota RFP list missing")

            pacific = pytz.timezone("US/Pacific")
            records = []
            for li in ul.find_all("li"):
                try:
                    code_span = (
                        li.find("span", class_="views-field-field-swift-event-id")
                        or li.find("span", class_="views-field-field-reference")
                        or li.find("span", class_="views-field-field-solicitation-number")
                    )
                    if not code_span:
                        raise ValueError("no code_span found")

                    content_span = code_span.find("span", class_="field-content")
                    if not content_span:
                        raise ValueError("code_span without .field-content")
                    code = content_span.get_text(strip=True)

                    title_span = li.find("span", class_="views-field-title")
                    if not title_span:
                        raise ValueError("no title_span found")
                    title_span = title_span.find("span", class_="field-content")
                    if not title_span:
                        raise ValueError("title_span without .field-content")
                    title = title_span.get_text(strip=True)

                    end_str = ""
                    due_container = li.find("span", class_="views-field-field-due-date")
                    if due_container:
                        time_tag = due_container.find("time", {"datetime": True})
                        if time_tag and time_tag["datetime"]:
                            dt_utc = datetime.fromisoformat(
                                time_tag["datetime"].replace("Z", "+00:00")
                            )
                            end_str = dt_utc.astimezone(pacific).strftime("%Y-%m-%d %H:%M:%S %Z")

                    link = STATE_RFP_URL_MAP.get('minnesota')
                    records.append({
                        "title": title,
                        "code": code,
                        "end_date": end_str,
                        "link": link,
                    })
                except Exception as e:
                    snippet = str(li)[:200].replace("\n", " ")
                    continue

            return pd.DataFrame(records)
        except DataExtractionError:
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Minnesota extract_data failed") from e


    # effects: orchestrates fetch -> extract_data -> filter; returns filtered records or raises
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Minnesota via HTML list")
        try:
            soup = self._fetch_page()
            df = self.extract_data(soup)
        except (SearchTimeoutError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"Minnesota search/extract failed: {e}", exc_info=True)
            raise ScraperError("Minnesota scrape failed") from e

        try:
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except Exception as e:
            self.logger.error(f"Minnesota scrape filter failed: {e}", exc_info=True)
            raise ScraperError("Minnesota scrape filter failed") from e
