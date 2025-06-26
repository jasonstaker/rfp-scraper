# pennsylvania.py
# url: https://www.emarketplace.state.pa.us/Search.aspx
import logging
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic

# Pennsylvania RFP portal scraper using Selenium
class PennsylvaniaScraper(SeleniumScraper):
    
    # requires: none
    # modifies: self
    # effects: initializes the scraper with Pennsylvania's RFP URL and configures logger
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("pennsylvania"))
        self.logger = logging.getLogger(__name__)

    # requires: none
    # modifies: self.driver
    # effects: navigates to the Pennsylvania RFP portal and waits for the main solicitations grid to load
    def search(self, **kwargs):
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "ctl00_MainBody_grdResults"))
            )
            return True
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise

    # requires: driver is on a loaded page of the RFP grid
    # modifies: none
    # effects: parses the solicitations table from current page and returns raw records list
    def extract_data(self):
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.find("table", id="ctl00_MainBody_grdResults")
            if not table:
                self.logger.error("Solicitations table not found")
                raise RuntimeError("Table not found")

            tbody = table.find("tbody")
            rows = tbody.find_all("tr", class_="GridItem") if tbody else []
            records = []

            for row in rows:
                try:
                    cols = row.find_all("td")
                    if len(cols) < 9:
                        continue

                    anchor = cols[0].find("a")
                    if not anchor:
                        continue
                    code = anchor.get_text(strip=True)
                    href = anchor.get("href")
                    link = urljoin(self.base_url, href)

                    label = cols[2].get_text(strip=True)

                    raw_date = cols[8].get_text(strip=True)
                    end_date = parse_date_generic(raw_date)

                    records.append({
                        "Label": label,
                        "Code": code,
                        "End (UTC-7)": end_date,
                        "Keyword Hits": "",
                        "Link": link,
                    })
                except Exception as row_ex:
                    self.logger.error(f"Failed processing row: {row_ex}")
                    continue

            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # requires: driver is on a page of the RFP grid
    # modifies: self.driver
    # effects: clicks the pager link for given page number; returns True if navigated, False otherwise
    def next_page(self, page_num):
        try:
            # build an XPath with proper escaping
            xpath = (
                f"//a[contains(@href, \"__doPostBack('ctl00$MainBody$grdResults','Page${page_num}')\")]"
            )
            next_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
        except TimeoutException:
            return False

        try:
            old_table = self.driver.find_element(By.ID, "ctl00_MainBody_grdResults")
            next_link.click()
            WebDriverWait(self.driver, 10).until(EC.staleness_of(old_table))
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "ctl00_MainBody_grdResults"))
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to navigate to page {page_num}: {e}")
            return False

    # requires: none
    # modifies: none
    # effects: orchestrates full scrape: search → extract_data (page 1) → paginate → DataFrame → filter → return records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Pennsylvania")
        all_records = []
        try:
            if not self.search(**kwargs):
                raise RuntimeError("Search did not complete successfully")

            all_records.extend(self.extract_data())

            page = 2
            while self.next_page(page):
                self.logger.info(f"Extracting page {page}")
                all_records.extend(self.extract_data())
                page += 1

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"Pennsylvania scrape failed: {e}", exc_info=True)
            raise
