# wyoming.py
# URL: https://www.publicpurchase.com/gems/wyominggsd,wy/buyer/public/publicInfo

import logging
import re
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, StaleElementReferenceException

import pandas as pd

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# a scraper for Wyoming RFP data using Selenium
class WyomingScraper(SeleniumScraper):
    # modifies: self
    # effects: initializes scraper with Wyoming PublicPurchase URL and configures logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("wyoming"))
        self.logger = logging.getLogger(__name__)

    # modifies: self.driver
    # effects: navigates to the Wyoming public purchase page and waits for the bid table rows
    def search(self, **kwargs):
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "table.tabHome tbody tr.listA td.lefttd a"
                ))
            )
            return True
        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            raise

    # requires: page loaded and JS populated the rows
    # effects: parses each table row into record dicts
    def extract_data(self):
        self.logger.info("Parsing Wyoming RFP table")
        records = []
        rows = self.driver.find_elements(
            By.CSS_SELECTOR,
            "table.tabHome tbody tr.listA, table.tabHome tbody tr.listB"
        )
        for row in rows:
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 5:
                    continue

                anchor = cols[0].find_element(By.TAG_NAME, "a")
                full_text = anchor.text.strip()

                code_match = re.search(r"#(\S+-K)", full_text)
                code = code_match.group(1) if code_match else ""

                if code:
                    label = re.sub(rf"#\s*{re.escape(code)}\s*-\s*", "", full_text).strip()
                else:
                    label = full_text

                link = anchor.get_attribute("href")

                end_text = cols[2].text.strip()
                date_tokens = end_text.split()[:3]  # e.g. ['Jun', '30,', '2025']
                date_str = " ".join(date_tokens)
                try:
                    dt = datetime.strptime(date_str, "%b %d, %Y")
                    end_date = dt.date().isoformat()
                except Exception:
                    end_date = date_str

                records.append({
                    "Label": label,
                    "Code": code,
                    "End (UTC-7)": end_date,
                    "Keyword Hits": "",
                    "Link": link,
                })

            except Exception as e:
                snippet = row.get_attribute("outerHTML")[:200].replace("\n", " ")
                self.logger.warning(f"Skipping row due to {e!r}. Snippet: {snippet}…")
                continue

        return records


    # requires: search() succeeded
    # modifies: self.driver
    # effects: orchestrates full scrape: search -> extract_data -> filter; returns list of dicts
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Wyoming")
        try:
            if not self.search(**kwargs):
                self.logger.error("Search failed; aborting Wyoming scrape")
                return []

            all_records = self.extract_data()
            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"Wyoming scrape failed: {e}", exc_info=True)
            raise
