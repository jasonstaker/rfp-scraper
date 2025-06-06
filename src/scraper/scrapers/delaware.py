# delaware.py
# url: https://mmp.delaware.gov/Bids

import logging
import time

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords


# a scraper class for Delaware RFP data using Selenium, including pagination.
class DelawareScraper(SeleniumScraper):

    # requires: none
    # modifies: self
    # effects: initializes the scraper with Delaware’s bids URL and sets up logging
    def __init__(self):
        super().__init__("https://mmp.delaware.gov/Bids")
        self.logger = logging.getLogger(__name__)

    # requires: none
    # modifies: self.driver
    # effects: opens the bids page and waits for the jqGrid to populate
    def search(self, **kwargs):
        try:
            self.driver.get(self.base_url)

            rows_xpath = "//table[@id='jqGridBids']/tbody/tr[contains(@class,'jqgrow')]"
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, rows_xpath))
            )
            return True

        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            return False

    # requires: none
    # modifies: none
    # effects: parses all rows in the jqGrid and returns a list of record dicts
    def extract_data(self):
        records = []
        try:
            table_xpath = "//table[@id='jqGridBids']"
            # ensure at least one data row is present
            row_xpath = f"{table_xpath}/tbody/tr[contains(@class,'jqgrow')]"
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, row_xpath))
            )

            # find all rows with class 'jqgrow'
            row_elements = self.driver.find_elements(By.XPATH, row_xpath)

            for row_el in row_elements:
                try:
                    cols = row_el.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 7:
                        continue

                    bid_id = cols[0].get_attribute("title").strip()
                    if not bid_id:
                        continue

                    code = cols[1].get_attribute("title").strip()

                    label = cols[2].text.strip()

                    closing_date = cols[4].get_attribute("title").strip()

                    # construct detail URL: “/Bids/Details/{bid_id}”
                    link = f"https://mmp.delaware.gov/Bids/Details/{bid_id}"

                    records.append({
                        "Label": label,
                        "Code": code,
                        "End (UTC-7)": closing_date,
                        "Keyword Hits": "",
                        "Link": link,
                    })

                except Exception as e:
                    self.logger.error(f"Failed processing a row: {e}", exc_info=False)
                    continue

            return records

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            return []

    # requires: none
    # modifies: self.driver
    # effects: clicks the “Next” button if enabled, waits for table to reload, returns True; else False
    def next_page(self):
        try:
            btn = self.driver.find_element(By.ID, "next_jqg1")
            btn_classes = btn.get_attribute("class")

            # if the button has 'disabled' class, no more pages
            if "disabled" in btn_classes:
                return False

            # click the Next button
            self.driver.execute_script("arguments[0].click();", btn)

            # wait for table to reload: wait for the first row of jqgrow to reappear
            row_xpath = "//table[@id='jqGridBids']/tbody/tr[contains(@class,'jqgrow')]"
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, row_xpath))
            )

            time.sleep(1)
            return True

        except Exception:
            return False

    # requires: none
    # modifies: self.logger
    # effects: orchestrates the scrape: search → extract_data → paginate → filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Delaware")
        all_records = []

        try:
            # load first page
            if not self.search(**kwargs):
                self.logger.warning("Search returned no results; aborting Delaware scrape")
                return []

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

            # build DataFrame and filter by keywords
            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"Delaware scrape failed: {e}", exc_info=True)
            raise
