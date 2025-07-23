# indiana.py
# url: https://www.in.gov/idoa/procurement/current-business-opportunities/

import logging

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from src.config import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# domain‑specific exceptions
from scraper.core.errors import (
    SearchTimeoutError,
    ElementNotFoundError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Indiana RFP data using Selenium
class IndianaScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with Indiana's RFP URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["indiana"])
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver (through selenium operations)
    # effects: navigates to the Indiana procurement page, waits for the events table to load, returns list of page HTML
    def search(self, **kwargs):
        self.logger.info("navigating to Indiana procurement page")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "events-table"))
            )
            return [self.driver.page_source]

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Indiana search timed out") from te

        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise ElementNotFoundError("Indiana search element not found") from ne

        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            raise ScraperError("Indiana search WebDriver error") from we

        except Exception as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            raise ScraperError("Indiana search failed") from e


    # requires: page_source is a string containing html page source
    # effects: parses the events table from page_source and returns a list of raw record dicts
    def extract_data(self, page_source):
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            raise DataExtractionError("Empty page_source for Indiana extract_data")

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            table = soup.find("table", id="events-table")
            if not table:
                self.logger.error("events-table not found")
                raise ElementNotFoundError("Indiana events table not found")

            tbody = table.find("tbody")
            if not tbody:
                self.logger.error("no <tbody> found in events-table")
                raise ElementNotFoundError("Indiana events <tbody> not found")

            records = []
            for row in tbody.find_all("tr", role="row"):
                cols = row.find_all("td")
                if len(cols) < 6:
                    continue

                title_a = cols[0].find("a")
                title = title_a.get_text(strip=True) if title_a else ""
                anchors = cols[0].find_all("a", href=True)
                download_link = (
                    f"https://www.in.gov{anchors[1]['href']}"
                    if len(anchors) > 1
                    else None
                )

                code = cols[2].get_text(strip=True)
                raw_due = cols[4].get_text(strip=True)

                records.append({
                    "title": title,
                    "code": code,
                    "end_date": raw_due,
                    "link": download_link,
                })

            return records

        except (ElementNotFoundError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Indiana extract_data failed") from e


    # effects: orchestrates the scraping process: search -> extract_data -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Indiana")
        try:
            html_list = self.search(**kwargs)
            if not html_list:
                self.logger.warning("Search returned no HTML; aborting Indiana scrape")
                raise ScraperError("Indiana scrape aborted due to empty search")

            all_records = []
            for html in html_list:
                all_records.extend(self.extract_data(html))

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"Indiana scrape failed: {e}", exc_info=True)
            raise ScraperError("Indiana scrape failed") from e
