# wisconsin.py
# url: https://esupplier.wi.gov/psp/esupplier_6/SUPPLIER/ERP/c/WI_SS_SELF_SERVICE.WI_SS_BIDDER_BIDS.GBL?Page=WI_SS_BIDDER_BIDS&Action=U

import logging
import time
from datetime import datetime, date

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, StaleElementReferenceException

import pandas as pd

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# a scraper for Wisconsin RFP data using Selenium
class WisconsinScraper(SeleniumScraper):
    # modifies: self
    # effects: initializes the scraper with Wisconsin’s portal URL and configures logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("wisconsin"))
        self.logger = logging.getLogger(__name__)

    # modifies: self.driver
    # effects: navigates to the Wisconsin bids page, switches into main content iframe, and waits for the grid
    def search(self, **kwargs):
        try:
            self.driver.get(self.base_url)
            
            iframe = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "ptifrmtgtframe"))
            )
            
            self.driver.switch_to.frame(iframe)
            
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.PSLEVEL1GRID"))
            )
            return True
        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            raise

    # requires: iframe switched and table present
    # effects: parses each row of the PSLEVEL1GRID into record dicts
    def extract_data(self, page_source=None):
        self.logger.info("Parsing Wisconsin RFP table")
        records = []
        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table.PSLEVEL1GRID tbody tr[id^='trWI_SS_BIDALL_VW']")
            for row in rows:
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 7:
                        continue

                    title = cols[3].text.strip()
                    code = cols[1].text.strip()
                    end_raw = cols[6].text.strip()
                    end_str = end_raw.rsplit(' ', 1)[0]

                    link_el = cols[1].find_element(By.TAG_NAME, "a")
                    href = link_el.get_attribute('href')
                    link = href if href and not href.startswith('javascript:') else self.base_url

                    records.append({
                        "title": title,
                        "code": code,
                        "end_date": end_str,
                        "link": link,
                    })
                except Exception as e:
                    snippet = row.get_attribute("outerHTML")[:200].replace("\n", " ")
                    self.logger.warning(f"Skipping row due to {e!r}. Snippet: {snippet}…")
                    continue
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # requires: search() succeeded and driver is within iframe
    # modifies: self.driver
    # effects: orchestrates full scrape with date-based pagination stop
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Wisconsin")
        try:
            if not self.search(**kwargs):
                self.logger.error("Search failed; aborting Wisconsin scrape")
                return []

            all_records = []
            today = date.today()

            while True:
                batch = self.extract_data()
                if not batch:
                    break

                try:
                    first_dt = datetime.strptime(batch[0]["end_date"], "%m/%d/%Y %I:%M%p").date()
                    if first_dt < today:
                        self.logger.info("Encountered record before today; stopping pagination")
                        break
                except Exception:
                    self.logger.warning("Failed to parse first record date; ending pagination")
                    all_records.extend(batch)
                    break

                all_records.extend(batch)

                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, "a.PTNEXTROW1")
                    if not next_btn.is_enabled():
                        break
                    next_btn.click()
                    WebDriverWait(self.driver, 20).until(EC.staleness_of(next_btn))
                    time.sleep(1)
                except (NoSuchElementException, WebDriverException, StaleElementReferenceException):
                    self.logger.info("No more pages or pagination error; ending loop")
                    break

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"Wisconsin scrape failed: {e}", exc_info=True)
            raise
