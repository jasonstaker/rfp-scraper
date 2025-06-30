# alabama.py
# url: https://procurement.staars.alabama.gov/PRDVSS1X1/AltSelfService

import logging

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# a scraper for Alabama RFP data using Selenium
class AlabamaScraper(SeleniumScraper):
    # modifies: self
    # effects: initializes the scraper with Alabama's RFP url and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["alabama"])
        self.logger = logging.getLogger(__name__)

    # modifies: self.driver
    # effects: navigates to the Alabama portal, opens the solicitiations table, and returns page source
    def search(self, **kwargs):
        self.logger.info("starting Alabama search")
        try:
            self.logger.debug("loading base URL")
            self.driver.get(self.base_url)

            self.logger.debug("waiting for publish button")
            pub = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="homelayout"]/td[1]/div/div[5]/div[3]/input'))
            )
            pub.click()

            self.logger.debug("switching to new window")
            WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > 1)
            new = [h for h in self.driver.window_handles if h != self.driver.current_window_handle][0]
            self.driver.switch_to.window(new)

            self.logger.debug("entering frame and opening solicitations")
            WebDriverWait(self.driver, 15).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "Display")))
            open_btn = self.driver.find_element(By.ID, "AMSBrowseOpenSolicit")
            WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable((By.ID, "AMSBrowseOpenSolicit")))
            self.driver.execute_script("arguments[0].click();", open_btn)

            self.logger.debug("waiting for table")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="PageContent"]/table[4]'))
            )
            self.logger.info("search successful")
            return self.driver.page_source

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}")
            raise
        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}")
            raise
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise

    # requires: page_source is a string containing html
    # effects: parses the HTML table into raw record dicts
    def extract_data(self, page_source):
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            raise
        self.logger.info("extracting Alabama records")
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
                items = [
                    td.get_text(strip=True)
                    for td in label_block.find_all("td", style=lambda s: s and "border-bottom" in s)
                ]
                label = items[0] if items else ""
                code = items[1] if len(items) > 1 else ""
                end_td = cols[2].find("td", style=lambda s: s and "color:red" in s)
                end_text = end_td.get_text(strip=True) if end_td else ""
                records.append({
                    "Label": label,
                    "Code": code,
                    "End (UTC-7)": end_text,
                    "Keyword Hits": "",
                    "Link": STATE_RFP_URL_MAP["alabama"],
                })
            self.logger.info(f"extracted {len(records)} Alabama records")
            return records

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # modifies: self.driver
    # effects: runs search -> pagination -> extract -> filter, returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("starting Alabama scrape")
        all_records = []
        try:
            page = self.search(**kwargs)
            if not page:
                self.logger.warning("search returned no page; skipping")
                raise

            self.logger.info("processing page 1")
            all_records.extend(self.extract_data(page))
            page_num = 2

            while True:
                try:
                    self.logger.debug(f"navigating to page {page_num}")
                    next_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="T1SO_SRCH_QRYnextpage"]'))
                    )
                    self.driver.execute_script("arguments[0].click();", next_btn)
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="PageContent"]/table[4]'))
                    )
                    self.logger.info(f"processing page {page_num}")
                    all_records.extend(self.extract_data(self.driver.page_source))
                    page_num += 1
                except TimeoutException:
                    self.logger.info("no more Alabama pages")
                    break
                except Exception:
                    self.logger.info("pagination ended")
                    break

            self.logger.info("parsing complete")
            df = pd.DataFrame(all_records)
            self.logger.info("applying filters")
            filtered = filter_by_keywords(df)
            self.logger.info(f"{len(filtered)} Alabama records after filtering")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"scrape failed: {e}", exc_info=True)
            raise
