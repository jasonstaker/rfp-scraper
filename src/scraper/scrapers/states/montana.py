# montana.py
# url: https://bids.sciquest.com/apps/Router/PublicEvent?CustomerOrg=StateOfMontana

import logging
import time

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, StaleElementReferenceException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# a scraper for Montana RFP data using Selenium
class MontanaScraper(SeleniumScraper):
    # modifies: self
    # effects: initializes the scraper with Montana’s portal URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["montana"])
        self.logger = logging.getLogger(__name__)

    # modifies: self.driver
    # effects: navigates to the Montana portal, waits for the main search-results table to appear
    def search(self, **kwargs):
        self.logger.info("navigating to Montana RFP portal")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/div[1]/div/div/div/div[2]/form/div[4]/div[2]/div/table",
                    )
                )
            )
            return True
        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            raise

    # requires: page_source is a string containing the HTML of one page
    # effects: parses the results table into a list of record dicts
    def extract_data(self, page_source):
        self.logger.info("parsing Montana RFP table")
        if not page_source:
            raise ValueError("empty page_source")

        soup = BeautifulSoup(page_source, "html.parser")
        tables = soup.find_all("table", attrs={"aria-label": "Search Results"})
        if not tables:
            tables = soup.find_all("table", attrs={"aria-title": "Search Results"})

        if not tables:
            self.logger.error("no Search Results table found")
            raise RuntimeError("table not found")

        table = tables[0]
        body = table.find("tbody") or table
        rows = body.find_all("tr")
        if not rows:
            self.logger.error("no rows found in Search Results table")
            raise RuntimeError("no rows")

        records = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            details_td = cols[1]
            link_a = details_td.select_one("a.btn.btn-link")
            if not link_a:
                continue
            title = link_a.get_text(strip=True)
            link  = link_a["href"]

            data_rows = details_td.select("div.phx.table-row-layout")

            def _find_value(suffix, strip_tz=False):
                for dr in data_rows:
                    id_div = dr.find("div", id=lambda i: i and suffix in i)
                    if id_div:
                        content = dr.select_one("div.phx.data-row-content")
                        if content:
                            text = content.get_text(strip=True)
                            if strip_tz:
                                # only strip trailing timezone token
                                return text.rsplit(" ", 1)[0]
                            return text
                return ""

            # only remove timezone from the Close date
            end_str = _find_value("LABEL_CLOSE")
            code    = _find_value("LABEL_NUMBER")

            records.append({
                "title":        title,
                "code":         code,
                "end_date":  end_str,
                "link":         link,
            })

        return records


    # modifies: self.driver (through pagination clicks)
    # effects: orchestrates search -> paginate -> extract_data -> DataFrame -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("starting Montana scrape")
        try:
            self.search(**kwargs)

            all_records = []
            while True:
                html = self.driver.page_source
                batch = self.extract_data(html)
                all_records.extend(batch)

                next_btn = self.driver.find_element(By.XPATH, "//button[@aria-label='Next page']")
                if next_btn.get_attribute("disabled"):
                    break

                try:
                    next_btn.click()
                    WebDriverWait(self.driver, 20).until(EC.staleness_of(next_btn))
                except (WebDriverException, StaleElementReferenceException) as e:
                    self.logger.error(f"pagination click failed: {e}", exc_info=False)
                    break

                time.sleep(1)

            df = pd.DataFrame(all_records)
            filtered = filter_by_keywords(df)
            self.logger.info(f"found {len(filtered)} records after filtering")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"scrape() failed: {e}", exc_info=True)
            raise
