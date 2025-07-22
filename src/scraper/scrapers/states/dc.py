# dc.py
# url: https://contracts.ocp.dc.gov/solicitations/search

import logging
from urllib.parse import urlparse, parse_qs

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# a scraper for District of Columbia RFP data using Selenium
class DCScraper(SeleniumScraper):
    # modifies: self
    # effects: initializes the scraper with DC's RFP URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["district of columbia"])
        self.logger = logging.getLogger(__name__)
        self.hash_token = None  # Will hold the "hash" query param after search

    # modifies: self.driver, self.hash_token
    # effects: navigates to DC portal, clicks "Search Solicitations", waits for results, captures hash token
    def search(self, **kwargs):
        try:
            self.driver.get(self.base_url)
            button_xpath = (
                "/html/body/app-root/div[2]/div/app-solicitations/"
                "app-solicitations-search/tabset/div/tab[1]/form/div[1]/div/div[2]/button[2]"
            )
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            ).click()
            WebDriverWait(self.driver, 20).until(
                lambda d: "/solicitations/results?hash=" in d.current_url
            )
            qs = parse_qs(urlparse(self.driver.current_url).query)
            self.hash_token = qs.get("hash", [None])[0]
            table_xpath = (
                "/html/body/app-root/div[2]/div/app-solicitations/"
                "app-solicitations-results/app-results-grid/"
                "div[2]/div[2]/div[2]/div/table"
            )
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, table_xpath))
            )
            return True
        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(f"search failed: {e}", exc_info=False)
            raise
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise

    # modifies: self.driver
    # effects: clicks "Next", waits for table reload, returns True if more pages exist
    def next_page(self):
        try:
            selector = "li.pagination-next.page-item:not(.disabled) a.page-link"
            link = self.driver.find_element(By.CSS_SELECTOR, selector)
            self.driver.execute_script("arguments[0].click();", link)
            table_xpath = (
                "/html/body/app-root/div[2]/div/app-solicitations/"
                "app-solicitations-results/app-results-grid/"
                "div[2]/div[2]/div[2]/div/table"
            )
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, table_xpath))
            )
            return True
        except (NoSuchElementException, TimeoutException):
            return False
        except WebDriverException as we:
            self.logger.error(f"next_page WebDriver error: {we}", exc_info=False)
            return False
        except Exception as e:
            self.logger.error(f"next_page failed: {e}", exc_info=True)
            return False

    # requires: self.hash_token is set
    # effects: parses each results row, builds detail URLs, returns list of record dicts
    def extract_data(self):
        records = []
        try:
            table_xpath = (
                "/html/body/app-root/div[2]/div/app-solicitations/"
                "app-solicitations-results/app-results-grid/"
                "div[2]/div[2]/div[2]/div/table"
            )
            table = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, table_xpath))
            )
            rows = self.driver.find_elements(By.XPATH, f"{table_xpath}/tbody/tr[@role='listitem']")
            for i in range(1, len(rows) + 1):
                try:
                    row_el = self.driver.find_element(
                        By.XPATH,
                        f"{table_xpath}/tbody/tr[@role='listitem'][{i}]"
                    )
                    code = row_el.find_element(By.XPATH, "./td[1]").text.strip()
                    title = row_el.find_element(By.XPATH, "./td[2]").text.strip()
                    closing = row_el.find_element(By.XPATH, "./td[5]").text.strip()
                    if self.hash_token:
                        link = (
                            f"https://contracts.ocp.dc.gov/solicitations/details"
                            f"?id={code}&hash={self.hash_token}"
                        )
                    else:
                        link = STATE_RFP_URL_MAP["district of columbia"]
                    records.append({
                        "title": title,
                        "code": code,
                        "end_date": closing,
                        "link": link,
                    })
                except Exception as e:
                    self.logger.error(f"Failed processing row {i}: {e}", exc_info=False)
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # effects: orchestrates search -> extract_data -> pagination -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for District of Columbia")
        all_records = []
        try:
            if not self.search(**kwargs):
                self.logger.warning("Search returned no results; aborting")
                raise
            all_records.extend(self.extract_data())
            page_num = 2
            while self.next_page():
                self.logger.info(f"Extracting data from page {page_num}")
                all_records.extend(self.extract_data())
                page_num += 1
            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except Exception as e:
            self.logger.error(f"DC scrape failed: {e}", exc_info=True)
            raise
