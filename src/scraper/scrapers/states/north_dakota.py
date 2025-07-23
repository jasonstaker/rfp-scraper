# north_dakota.py
# url: https://apps.nd.gov/csd/spo/services/bidder/searchSolicitation.do

import logging
from datetime import datetime
from urllib.parse import quote, urljoin

import pandas as pd
from bs4 import BeautifulSoup

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords
from src.config import STATE_RFP_URL_MAP
from scraper.core.errors import (
    SearchTimeoutError,
    ElementNotFoundError,
    DataExtractionError,
    ScraperError,
)

# a scraper for North Dakota RFP data using Selenium
class NorthDakotaScraper(SeleniumScraper):

    # effects: initialize with base URL and logger
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["north dakota"] + "&")
        self.logger = logging.getLogger(__name__)


    # effects: navigate home, click 'Search All Solicitations', then go to daily URL
    def search(self, **kwargs):
        self.logger.info("Navigating to North Dakota solicitations")
        try:
            today = datetime.now().strftime("%m/%d/%Y")
            start = quote(today, safe="")
            stop = quote("12/31/2100", safe="")
            base_no_amp = self.base_url.rstrip("&")
            search_url = f"{base_no_amp}&searchDT.startDate={start}&searchDT.stopDate={stop}"

            self.driver.get(base_no_amp)
            self.logger.info(f"Loading search URL: {search_url}")
            self.driver.get(search_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    '/html/body/div[1]/div[4]/div/section/div[3]/form/div/table'
                ))
            )
            return True
        except TimeoutException as te:
            self.logger.error(f"Search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("North Dakota search timed out") from te
        except NoSuchElementException as ne:
            self.logger.error(f"Search element not found: {ne}", exc_info=False)
            raise ElementNotFoundError("North Dakota search element not found") from ne
        except WebDriverException as we:
            self.logger.error(f"Search WebDriver error: {we}", exc_info=True)
            raise ScraperError("North Dakota search WebDriver error") from we
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise ScraperError("North Dakota search failed") from e


    # effects: parse table into record list
    def extract_data(self):
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.find("table", summary="Results from Project Search")
            if not table:
                self.logger.error("Results table not found")
                raise ElementNotFoundError("North Dakota results table not found")

            records = []
            for tr in table.find_all("tr")[1:]:
                cols = tr.find_all("td")
                if len(cols) < 4:
                    continue
                date = cols[0].get_text(strip=True)
                code = cols[1].get_text(strip=True)
                title = cols[2].get_text(strip=True)
                records.append({
                    "title": title,
                    "code": code,
                    "end_date": date,
                    "link": self.driver.current_url,
                })

            return records
        except ElementNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("North Dakota extract_data failed") from e


    # effects: orchestrate search, extract, filter, return
    def scrape(self, **kwargs):
        self.logger.info("Starting North Dakota scrape")
        try:
            if not self.search(**kwargs):
                self.logger.warning("Search returned no results; aborting")
                raise ScraperError("North Dakota scrape aborted due to empty search")

            recs = self.extract_data()
            df = pd.DataFrame(recs)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"North Dakota scrape failed: {e}", exc_info=True)
            raise ScraperError("North Dakota scrape failed") from e
