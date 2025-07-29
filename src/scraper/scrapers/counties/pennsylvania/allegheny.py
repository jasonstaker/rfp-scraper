# allegheny.py
# url: https://solicitations.alleghenycounty.us/

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

# a scraper for Allegheny County, PA solicitations via HTML parsing
class AlleghenyScraper(RequestsScraper):

    # effects: initializes with Allegheny solicitations URL and logger
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP["pennsylvania"]["allegheny"])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })


    # effects: GETs the homepage with postings; returns HTML
    def search(self, **kwargs):
        try:
            resp = self.session.get(self.base_url, timeout=20)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            self.logger.error(f"search HTTP error: {e}", exc_info=False)
            raise SearchTimeoutError("Allegheny search HTTP error") from e


    # requires: HTML string from search()
    # effects: parses section.homepage >> div.postBox elements into records
    def extract_data(self, html):
        try:
            soup = BeautifulSoup(html, "html.parser")
            section = soup.find("section", class_="homepage")
            if not section:
                raise DataExtractionError("Allegheny homepage section not found")
            boxes = section.find_all("div", class_="postBox")

            records = []
            for box in boxes:
                article = box.find("article")
                if not article:
                    continue
                
                art_id = article.get("id", "")
                code = art_id.split('-')[-1] if art_id else ""
                
                h2 = article.select_one("div.leftSide h2 a")
                title = h2.get_text(strip=True) if h2 else ""
                href = h2["href"] if h2 and h2.has_attr("href") else ""
                link = href if href.startswith("http") else urljoin(self.base_url, href)
                
                dd = article.select_one("div.rightSide .dd p strong")
                raw_due = dd.get_text(strip=True) if dd else ""
                try:
                    due_dt = datetime.strptime(raw_due, "%A, %B %d, %Y")
                    due_date = due_dt.strftime("%Y-%m-%d")
                except Exception:
                    due_date = raw_due

                records.append({
                    "code": code,
                    "title": title,
                    "end_date": due_date,
                    "link": link,
                })

            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Allegheny extract_data failed") from e


    # effects: orchestrates search -> extract_data -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Allegheny County, PA")
        try:
            html = self.search(**kwargs)
            raw = self.extract_data(html)
            df = pd.DataFrame(raw)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except (SearchTimeoutError, DataExtractionError) as e:
            self.logger.error(f"Allegheny scrape failed: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Allegheny scrape unexpected error: {e}", exc_info=True)
            raise ScraperError("Allegheny scrape failed") from e