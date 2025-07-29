# tarrant.py
# url: https://tarrantcountytx.ionwave.net/SourcingEvents.aspx?SourceType=1

import logging
import pandas as pd
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords
from src.config import COUNTY_RFP_URL_MAP
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    PaginationError,
    ScraperError,
)

# a scraper for Tarrant County solicitations using Selenium
class TarrantScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with Tarrant County's bid portal URL and sets up logging
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP['texas']['tarrant'])
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: navigates to the Tarrant County solicitations page and waits for the bids table to be visible
    def search(self, **kwargs):
        self.logger.info("Navigating to Tarrant County bid portal")
        try:
            self.driver.get(self.base_url)
            
            WebDriverWait(self.driver, 20).until(
                EC.visibility_of_element_located((By.ID, 'ctl00_mainContent_rgBidList_ctl00'))
            )
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#ctl00_mainContent_rgBidList_ctl00 tbody tr'))
            )
            return True

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Tarrant search timed out") from te

        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            raise ScraperError("Tarrant search WebDriver error") from we

        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("Tarrant search failed") from e


    # effects: parses the bids table and extracts raw record dicts
    def extract_data(self):
        try:
            records = []
            table = self.driver.find_element(By.ID, 'ctl00_mainContent_rgBidList_ctl00')
            rows = table.find_elements(By.CSS_SELECTOR, 'tbody > tr')

            for idx, row in enumerate(rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if len(cells) < 7:
                        continue

                    code = cells[1].text.strip()
                    title = cells[2].text.strip()
                    close_date = cells[6].text.strip()

                    if not code or not title:
                        self.logger.warning(f"[Row {idx}] Missing code/title; skipping")
                        continue

                    records.append({
                        'code': code,
                        'title': title,
                        'end_date': close_date,
                        'link': self.base_url,
                    })

                except Exception as e:
                    self.logger.error(f"[Row {idx}] Error parsing row: {e}", exc_info=False)
                    continue

            return records

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Tarrant extract_data failed") from e


    # effects: orchestrates search -> extract_data -> paginate -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Tarrant County")
        try:
            if not self.search(**kwargs):
                raise ScraperError("Tarrant scrape aborted due to search failure")

            seen = set()
            all_records = []
            page = 1

            while True:
                self.logger.info(f"Processing page {page}")
                
                batch = self.extract_data()
                new_batch = [rec for rec in batch if rec['code'] not in seen]
                for rec in new_batch:
                    seen.add(rec['code'])

                if not new_batch:
                    self.logger.info("No new records found; stopping pagination")
                    break

                all_records.extend(new_batch)

                try:
                    next_btn = self.driver.find_element(By.CLASS_NAME, 'rgPageNext')
                    if not next_btn.is_enabled() or not next_btn.is_displayed():
                        self.logger.info("Next button disabled/hidden; end of pages")
                        break
                    
                    table = self.driver.find_element(By.ID, 'ctl00_mainContent_rgBidList_ctl00')
                    next_btn.click()
                    
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '#ctl00_mainContent_rgBidList_ctl00 tbody tr'))
                    )
                except NoSuchElementException:
                    self.logger.info("Next button not found; end of pages")
                    break
                except WebDriverException as we:
                    self.logger.error(f"Pagination click failed: {we}", exc_info=False)
                    raise PaginationError("Tarrant pagination failed") from we

                page += 1

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict('records')

        except (SearchTimeoutError, DataExtractionError, PaginationError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"Tarrant scrape failed: {e}", exc_info=True)
            raise ScraperError("Tarrant scrape failed") from e
