# alabama.py
# url: https://procurement.staars.alabama.gov/PRDVSS1X1/AltSelfService

import logging
import time

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# a scraper class for alabama rfp data using selenium
class AlabamaScraper(SeleniumScraper):
    # requires: nothing
    # modifies: self
    # effects: initializes the scraper with alabama's rfp url and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["alabama"])
        self.logger = logging.getLogger(__name__)

    # requires: nothing
    # modifies: self.driver (through selenium operations)
    # effects: navigates to the alabama rfp portal, performs necessary clicks to load the solicitations table, and returns the page source if successful, otherwise none
    def search(self, **kwargs):
        try:
            self.driver.get(self.base_url)
            pub_locator = (By.XPATH, '//*[@id="homelayout"]/td[1]/div/div[5]/div[3]/input')
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(pub_locator)).click()
            WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > 1)
            new_handle = [h for h in self.driver.window_handles if h != self.driver.current_window_handle][0]
            self.driver.switch_to.window(new_handle)
            WebDriverWait(self.driver,15).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "Display")))
            open_locator = (By.ID, "AMSBrowseOpenSolicit")
            WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable(open_locator))
            self.driver.execute_script("arguments[0].click();", self.driver.find_element(*open_locator))
            tableLocator = (By.XPATH, '//*[@id="PageContent"]/table[4]')
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(tableLocator))
            return self.driver.page_source
        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise
        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise

    # requires: page_source is a string containing html page source
    # modifies: nothing
    # effects: parses the html table from page_source and returns a list of raw records
    def extract_data(self, page_source):
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            raise
        try:
            soup = BeautifulSoup(page_source, "html.parser")
            table = soup.find("table", attrs={"name": "tblT1SO_SRCH_QRY"})
            if not table:
                self.logger.error("table not found in extract_data")
                raise
            records = []
            rows = table.find_all("tr", class_=lambda c: c and "advgrid" in c.lower())
            for row in rows:
                cols = row.find_all("td", valign="top")
                if len(cols) < 4:
                    continue
                label_block = cols[0]
                text_items = [
                    td.get_text(strip=True)
                    for td in label_block.find_all("td", style=lambda s: s and "border-bottom" in s)
                ]
                label = text_items[0] if len(text_items) > 0 else ""
                code = text_items[1] if len(text_items) > 1 else ""
                end_text = ""
                end_td = cols[2].find("td", style=lambda s: s and "color:red" in s)
                if end_td:
                    end_text = end_td.get_text(strip=True)
                link = STATE_RFP_URL_MAP["alabama"]
                records.append(
                    {
                        "Label": label,
                        "Code": code,
                        "End (UTC-7)": end_text,
                        "Keyword Hits": "",
                        "Link": link,
                    }
                )
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # requires: nothing
    # modifies: self.driver (through selenium operations)
    # effects: orchestrates the scraping process: search → paginate → extract → filter; returns filtered records, raises exception on failure
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Alabama")
        all_records = []
        try:
            page = self.search(**kwargs)
            if not page:
                self.logger.warning("Search returned no page; skipping extraction")
                raise
            self.logger.info("Processing page 1")
            all_records.extend(self.extract_data(page))
            page_num = 2
            while True:
                try:
                    next_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="T1SO_SRCH_QRYnextpage"]'))
                    )
                    self.driver.execute_script("arguments[0].click();", next_btn)
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="PageContent"]/table[4]'))
                    )
                    self.logger.info(f"Processing page {page_num}")
                    all_records.extend(self.extract_data(self.driver.page_source))
                    page_num += 1
                except TimeoutException:
                    self.logger.info("No more pages or pagination timeout")
                    break
                except Exception:
                    self.logger.info("Pagination ended")
                    break
            self.logger.info("Completed parsing")
            df = pd.DataFrame(all_records)
            self.logger.info("Applying filters")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Found {len(filtered)} records after filtering")
            return filtered.to_dict("records")
        except Exception as e:
            self.logger.error(f"Scrape failed: {e}", exc_info=True)
            # Now raise so main.py can retry up to 3 times
            raise