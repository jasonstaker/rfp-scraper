# delaware.py
# url: https://mmp.delaware.gov/Bids

import logging
import pandas as pd
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords

from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    PaginationError,
    ScraperError,
)

# a scraper for Delaware RFP data using Selenium
class DelawareScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with Delaware's bids URL and sets up logging
    def __init__(self):
        super().__init__("https://mmp.delaware.gov/Bids")
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: opens the bids page and waits for the jqGrid to populate
    def search(self, **kwargs):
        try:
            self.driver.get(self.base_url)
            rows_xpath = "//table[@id='jqGridBids']/tbody/tr[contains(@class,'jqgrow')]"
            WebDriverWait(self.driver, 20).until(
                EC.visibility_of_all_elements_located((By.XPATH, rows_xpath))
            )
            return True
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise SearchTimeoutError("Delaware search failed") from e


    # effects: parses all rows in the jqGrid and returns a list of record dicts
    def extract_data(self):
        try:
            records = []
            table_xpath = "//table[@id='jqGridBids']"
            all_rows = self.driver.find_elements(By.XPATH, f"{table_xpath}/tbody/tr")

            for idx, row_el in enumerate(all_rows):
                classes = row_el.get_attribute('class') or ''
                
                if 'jqgfirstrow' in classes:
                    self.logger.info(f"[Row {idx}] Skipping header/fake row")
                    continue
                
                if 'jqgrow' not in classes:
                    self.logger.info(f"[Row {idx}] Skipping non-data row (classes: {classes})")
                    continue

                cols = row_el.find_elements(By.TAG_NAME, 'td')
                
                if len(cols) < 7:
                    self.logger.warning(f"[Row {idx}] Skipped due to insufficient columns ({len(cols)})")
                    continue

                try:
                    bid_id = (cols[0].get_attribute('title') or cols[0].text).strip()
                    code = (cols[1].get_attribute('title') or cols[1].text).strip()
                    title = (cols[2].get_attribute('title') or cols[2].text).strip()
                    closing_date = (cols[4].get_attribute('title') or cols[4].text).strip()

                    if not bid_id:
                        self.logger.warning(f"[Row {idx}] Missing bid_id. Skipping.")
                        continue

                    link = f"https://mmp.delaware.gov/Bids/Details/{bid_id}"
                    records.append({
                        'title': title,
                        'code': code,
                        'end_date': closing_date,
                        'link': link,
                    })
                except Exception as e:
                    self.logger.error(f"[Row {idx}] Error parsing row: {e}", exc_info=False)

            return records

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Delaware extract_data failed") from e


    # modifies: self.driver
    # effects: clicks the Next Page button until it becomes disabled, returns True if moved to next page, else False
    def next_page(self):
        try:
            btn = self.driver.find_element(By.ID, "next_jqg1")
            classes = btn.get_attribute("class") or ""
            
            if "disabled" in classes:
                return False

            self.driver.execute_script("arguments[0].click();", btn)

            row_xpath = "//table[@id='jqGridBids']/tbody/tr[contains(@class,'jqgrow')]"
            WebDriverWait(self.driver, 20).until(
                EC.staleness_of(self.driver.find_element(By.XPATH, row_xpath))
            )
            WebDriverWait(self.driver, 20).until(
                EC.visibility_of_all_elements_located((By.XPATH, row_xpath))
            )
            return True
        except WebDriverException as we:
            self.logger.error(f"next_page WebDriver error: {we}", exc_info=False)
            raise PaginationError("Delaware pagination failed") from we
        except Exception:
            return False


    # effects: orchestrates search -> extract_data -> paginate -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Delaware")
        try:
            if not self.search(**kwargs):
                self.logger.warning("Search returned no results; aborting Delaware scrape")
                raise ScraperError("Delaware scrape aborted due to search failure")

            all_records = []
            self.logger.info("Extracting data from page 1")
            all_records.extend(self.extract_data())

            page = 2
            while self.next_page():
                self.logger.info(f"Extracting data from page {page}")
                all_records.extend(self.extract_data())
                page += 1

            self.logger.info("No more pages or pagination ended")
            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict('records')

        except (SearchTimeoutError, DataExtractionError, PaginationError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"Delaware scrape failed: {e}", exc_info=True)
            raise ScraperError("Delaware scrape failed") from e
