# north_carolina.py
# url: https://evp.nc.gov/solicitations/

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# a scraper for North Carolina RFP data using Selenium
class NorthCarolinaScraper(SeleniumScraper):
    # modifies: self
    # effects: initializes scraper with North Carolina RFP URL and configures logger
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("north carolina"))
        self.logger = logging.getLogger(__name__)

    # modifies: self.driver
    # effects: navigates to the North Carolina portal and waits for initial table rows to load
    def search(self, **kwargs):
        self.logger.info("Navigating to North Carolina RFP portal")
        try:
            self.driver.get(self.base_url)
            # Wait until at least one row is present in the solicitations table
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "table.table-striped.table-fluid tbody tr"
                ))
            )
            return True
        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise

    # requires: current page loaded in self.driver
    # effects: parses the solicitations table and returns list of raw records
    def extract_data(self):
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.find("table", class_="table table-striped table-fluid")
            if not table:
                self.logger.error("Solicitations table not found")
                return []

            tbody = table.find("tbody")
            if not tbody:
                self.logger.error("<tbody> not found in table")
                return []

            records = []
            for row in tbody.find_all("tr", attrs={"data-entity": "evp_solicitation"}):
                cols = row.find_all("td")
                if len(cols) < 7:
                    continue

                # Solicitation Number and link
                a = cols[0].find("a", href=True)
                code = a.get_text(strip=True) if a else ""
                link = urljoin(self.base_url, a["href"]) if a else self.base_url

                # Project Title
                title = cols[1].get_text(strip=True)

                # Description (not stored but could be logged)
                # desc = cols[2].get_text(strip=True)

                # Opening Date as end date
                time_tag = cols[3].find("time")
                end_date = time_tag.get_text(strip=True) if time_tag else cols[3].get_text(strip=True)

                records.append({
                    "Label": title,
                    "Code": code,
                    "End (UTC-7)": end_date,
                    "Keyword Hits": "",
                    "Link": link,
                })

            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # modifies: self.driver
    # effects: clicks next page if available, returns True if click succeeded
    def next_page(self):
        try:
            # only clickable when aria-disabled is not true
            next_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "a.entity-pager-next-link:not([aria-disabled='true'])"
                ))
            )
        except TimeoutException:
            return False

        try:
            # wait for current table to go stale
            old_tbody = self.driver.find_element(By.CSS_SELECTOR, "table.table-striped.table-fluid tbody")
            next_btn.click()
            WebDriverWait(self.driver, 10).until(EC.staleness_of(old_tbody))
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-striped.table-fluid tbody tr"))
            )
            return True
        except (TimeoutException, WebDriverException):
            return False

    # effects: orchestrates full scrape: search -> extract_data & paginate -> filter -> return
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for North Carolina")
        all_records = []
        try:
            if not self.search(**kwargs):
                self.logger.warning("Search did not initialize correctly; aborting")
                raise RuntimeError("NorthCarolinaScraper.search() failed")

            page = 1
            while True:
                self.logger.info(f"Extracting page {page}")
                batch = self.extract_data()
                if page == 1 and not batch:
                    self.logger.error("No records found on first page; aborting")
                    raise RuntimeError("NorthCarolinaScraper.extract_data() returned empty on first page")
                all_records.extend(batch)

                if not self.next_page():
                    self.logger.info("No more pages to process; ending pagination")
                    break
                page += 1

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"scrape failed: {e}", exc_info=True)
            raise
