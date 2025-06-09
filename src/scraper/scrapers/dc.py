# dc.py
# url: https://contracts.ocp.dc.gov/solicitations/search

import logging
import time
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


class DCScraper(SeleniumScraper):
    # requires: none
    # modifies: self
    # effects: initializes the scraper with DC's RFP URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["district of columbia"])
        self.logger = logging.getLogger(__name__)
        self.hash_token = None  # Will hold the “hash” query param after search

    # requires: none
    # modifies: self.driver, self.hash_token
    # effects: navigates to DC RFP portal, clicks "Search Solicitations", waits for results page, captures hash from URL
    def search(self, **kwargs):
        try:
            self.driver.get(self.base_url)

            # Wait for “Search Solicitations” button and click it
            button_xpath = (
                "/html/body/app-root/div[2]/div/app-solicitations/"
                "app-solicitations-search/tabset/div/tab[1]/form/div[1]/div/div[2]/button[2]"
            )
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            ).click()

            # wait until URL changes to include “/results?hash=…”
            WebDriverWait(self.driver, 20).until(
                lambda d: "/solicitations/results?hash=" in d.current_url
            )

            # extract “hash” query parameter from current URL
            parsed = urlparse(self.driver.current_url)
            qs = parse_qs(parsed.query)
            hashes = qs.get("hash", [])
            if hashes:
                self.hash_token = hashes[0]
            else:
                self.hash_token = None
                self.logger.warning("No hash token found in URL")

            # wait for results table to load
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

    # requires: none
    # modifies: self.driver
    # effects: clicks “Next” if available, waits for table to reload, returns True/False
    def next_page(self):
        try:
            next_selector = "li.pagination-next.page-item:not(.disabled) a.page-link"
            next_link = self.driver.find_element(By.CSS_SELECTOR, next_selector)
            self.driver.execute_script("arguments[0].click();", next_link)

            # wait for table to reload (URL remains “/results?hash=…”)
            table_xpath = (
                "/html/body/app-root/div[2]/div/app-solicitations/"
                "app-solicitations-results/app-results-grid/"
                "div[2]/div[2]/div[2]/div/table"
            )
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, table_xpath))
            )

            time.sleep(1)
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
    # modifies: none
    # effects: parses each row in the results table, constructs detail URLs using code + hash, returns list of dicts
    def extract_data(self):
        records = []
        try:
            table_xpath = (
                "/html/body/app-root/div[2]/div/app-solicitations/"
                "app-solicitations-results/app-results-grid/"
                "div[2]/div[2]/div[2]/div/table"
            )
            # ensure table is present
            table = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, table_xpath))
            )

            # count how many rows are on this page
            row_elems = self.driver.find_elements(By.XPATH, f"{table_xpath}/tbody/tr[@role='listitem']")
            total_rows = len(row_elems)

            for i in range(1, total_rows + 1):
                try:
                    # re-locate row i via fresh XPath
                    row_el = self.driver.find_element(
                        By.XPATH,
                        f"{table_xpath}/tbody/tr[@role='listitem'][{i}]"
                    )

                    # extract solicitation code, title, and closing date
                    code = row_el.find_element(By.XPATH, "./td[1]").text.strip()
                    label = row_el.find_element(By.XPATH, "./td[2]").text.strip()
                    closing_date = row_el.find_element(By.XPATH, "./td[5]").text.strip()

                    # construct detail URL: base + ?id={code}&hash={hash_token}
                    if self.hash_token:
                        link = (
                            f"https://contracts.ocp.dc.gov/solicitations/details"
                            f"?id={code}&hash={self.hash_token}"
                        )
                    else:
                        link = STATE_RFP_URL_MAP["district of columbia"]

                    records.append({
                        "Label": label,
                        "Code": code,
                        "End (UTC-7)": closing_date,
                        "Keyword Hits": "",
                        "Link": link,
                    })

                except Exception as e:
                    self.logger.error(f"Failed processing row {i}: {e}", exc_info=False)
                    continue

            return records

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # requires: none
    # modifies: self.logger
    # effects: orchestrates the scrape: search → extract_data → paginate → filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for District of Columbia")
        all_records = []

        try:
            # first page
            if not self.search(**kwargs):
                self.logger.warning("Search returned no results; aborting")
                raise

            self.logger.info("Extracting data from page 1")
            all_records.extend(self.extract_data())

            # pagination loop
            page_num = 2
            while True:
                if not self.next_page():
                    self.logger.info("No more pages or pagination ended")
                    break

                self.logger.info(f"Extracting data from page {page_num}")
                all_records.extend(self.extract_data())
                page_num += 1

            # build DataFrame and apply keyword filter
            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"DC scrape failed: {e}", exc_info=True)
            raise
