# wayne.py
# url: https://www.bidnetdirect.com/mitn/county-of-wayne

import logging
import pandas as pd
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords
from src.config import COUNTY_RFP_URL_MAP
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Wayne County open solicitations using Selenium
class WayneScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with Wayne County's BidNet URL and sets up logging
    def __init__(self):
        base_url = COUNTY_RFP_URL_MAP['michigan']['wayne']
        super().__init__(base_url)
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: navigates to the Wayne County solicitations page and waits for the table to be visible
    def search(self, **kwargs):
        try:
            self.logger.info("Navigating to Wayne County RFP page")
            self.driver.get(self.base_url)

            WebDriverWait(self.driver, 20).until(
                EC.visibility_of_element_located((By.ID, 'g_6'))
            )
            WebDriverWait(self.driver, 20).until(
                EC.visibility_of_element_located(
                    (By.XPATH, '/html/body/main/div[1]/div/div/div[1]/div/div[1]/div[4]/div/div/form/table')
                )
            )
            return True

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Wayne search timed out") from te

        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            raise ScraperError("Wayne search WebDriver error") from we

        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("Wayne search failed") from e


    # effects: parses the solicitations table and extracts raw record dicts
    def extract_data(self):
        try:
            records = []
            rows = self.driver.find_elements(
                By.CSS_SELECTOR,
                '#g_6 tbody tr.mets-table-row'
            )

            for idx, row in enumerate(rows):
                try:
                    sol_num = row.find_element(By.CSS_SELECTOR, 'div.sol-num').text.strip()
                    title_el = row.find_element(By.CSS_SELECTOR, 'a.solicitation-link')
                    title = title_el.text.strip()
                    link = title_el.get_attribute('href').strip()

                    closing_date = row.find_element(
                        By.CSS_SELECTOR,
                        'span.sol-closing-date .date-value'
                    ).text.strip()

                    if not sol_num or not title:
                        self.logger.warning(f"[Row {idx}] Missing data; skipping")
                        continue

                    records.append({
                        'title': title,
                        'code': sol_num,
                        'end_date': closing_date,
                        'link': link,
                    })

                except Exception as e:
                    self.logger.error(f"[Row {idx}] Error parsing row: {e}", exc_info=False)
                    continue

            return records

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Wayne extract_data failed") from e


    # effects: orchestrates search -> extract_data -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Wayne County")
        try:
            if not self.search(**kwargs):
                self.logger.warning("Search returned no results; aborting Wayne scrape")
                raise ScraperError("Wayne scrape aborted due to search failure")

            raw = self.extract_data()
            df = pd.DataFrame(raw)
            self.logger.info(f"Total raw records before filtering: {len(df)}")

            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict('records')

        except (SearchTimeoutError, DataExtractionError, ScraperError):
            raise

        except Exception as e:
            self.logger.error(f"scrape failed: {e}", exc_info=True)
            raise ScraperError("Wayne scrape failed") from e
