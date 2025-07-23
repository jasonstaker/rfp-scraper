# hawaii.py
# url: https://hiepro.ehawaii.gov/solicitation-notices.html

import logging
import time

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

from scraper.core.errors import (
    SearchTimeoutError,
    ElementNotFoundError,
    DataExtractionError,
    PaginationError,
    ScraperError,
)

# a scraper for Hawaii RFP data using Selenium
class HawaiiScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with Hawaii's RFP URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["hawaii"])
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: navigates to the page, clicks search links/buttons to load data, and returns page source
    def search(self, **kwargs):
        self.logger.info("Navigating to Hawaii solicitation page")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.requiring-confirmation[href="/sav-search.html"]'))
            ).click()
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.ID, 'search_button1'))
            ).click()
            WebDriverWait(self.driver, 30).until(
                lambda d: any(
                    td.text.strip() for td in d.find_elements(By.CSS_SELECTOR, '#notices-list tbody tr td:nth-of-type(9)')
                )
            )
            return self.driver.page_source

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Hawaii search timed out") from te

        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise ElementNotFoundError("Hawaii search element not found") from ne

        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("Hawaii search failed") from e


    # modifies: self.driver
    # effects: clicks 'Next' pagination button and waits for table refresh; returns True if next page exists
    def next_page(self):
        try:
            next_btn = self.driver.find_element(By.ID, 'notices-list_next')
            if 'disabled' in next_btn.get_attribute('class'):
                return False

            table = self.driver.find_element(By.ID, 'notices-list')
            old_first = table.find_element(By.CSS_SELECTOR, 'tbody tr').text

            self.driver.execute_script("arguments[0].click();", next_btn)

            WebDriverWait(self.driver, 20).until(
                lambda d: d.find_element(By.CSS_SELECTOR, '#notices-list tbody tr').text != old_first
            )
            return True

        except (TimeoutException, NoSuchElementException):
            return False

        except WebDriverException as we:
            self.logger.error(f"next_page WebDriver error: {we}", exc_info=False)
            raise PaginationError("Hawaii pagination failed") from we

        except Exception as e:
            self.logger.error(f"next_page failed: {e}", exc_info=True)
            raise ScraperError("Hawaii next_page failed") from e


    # requires: page_source containing the notices-list table
    # effects: parses table rows into records
    def extract_data(self, page_source):
        self.logger.info("Parsing HTML for Hawaii records")
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            raise DataExtractionError("Empty page_source for Hawaii extract_data")

        try:
            soup = BeautifulSoup(page_source, 'html.parser')
            table = soup.find('table', id='notices-list')
            if not table:
                self.logger.error("notices-list table not found")
                raise ElementNotFoundError("Hawaii results table not found")
            tbody = table.find('tbody')
            if not tbody:
                self.logger.error("no <tbody> found in table")
                raise ElementNotFoundError("Hawaii results <tbody> not found")
            rows = tbody.find_all('tr')
            records = []
            for tr in rows:
                cols = tr.find_all('td')
                code_tag = cols[0].find('a', href=True)
                if not code_tag:
                    continue
                code = code_tag.text.strip()
                href = code_tag['href']
                link = href if href.startswith('http') else f"https://hiepro.ehawaii.gov/{href}"
                title = cols[2].get_text(strip=True)
                end_datetime = cols[8].get_text(strip=True)

                records.append({
                    'title': title,
                    'code': code,
                    'end_date': end_datetime,
                    'link': link,
                })
            return records

        except (ElementNotFoundError, DataExtractionError):
            raise

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Hawaii extract_data failed") from e


    # modifies: self.driver
    # effects: orchestrates the scrape: search -> extract -> paginate -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Hawaii")
        all_records = []

        try:
            page_source = self.search(**kwargs)
            all_records.extend(self.extract_data(page_source))

            while self.next_page():
                self.logger.info("Extracting next page")
                time.sleep(1)  # allow DOM settle
                all_records.extend(self.extract_data(self.driver.page_source))

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict('records')

        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, PaginationError, ScraperError):
            raise

        except Exception as e:
            self.logger.error(f"Hawaii scrape failed: {e}", exc_info=True)
            raise ScraperError("Hawaii scrape failed") from e
