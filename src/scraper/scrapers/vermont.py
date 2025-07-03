# vermont.py
# url: https://www.vermontbusinessregistry.com/BidSearch.aspx?type=1

import logging
import re
import pandas as pd
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# a scraper for Vermont RFP data using Selenium
class VermontScraper(SeleniumScraper):
    # requires: STATE_RFP_URL_MAP['vermont'] = search page URL
    # modifies: self
    # effects: initializes scraper with Vermont search URL and logger
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP['vermont'])
        self.logger = logging.getLogger(__name__)

    # modifies: self.driver
    # effects: navigates to the search page and waits for the results table
    def search(self, **kwargs):
        try:
            self.logger.info("Navigating to Vermont RFP portal")
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, 'gvResults'))
            )
            return True
        except TimeoutException as e:
            self.logger.error(f"search() timeout: {e}", exc_info=True)
            raise

    # requires: current page loaded in self.driver
    # effects: parses the gvResults table into a list of records
    def extract_data(self):
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        table = soup.find('table', id='gvResults')
        if not table:
            self.logger.error("Results table not found")
            return []

        tbody = table.find('tbody') or table
        rows = tbody.find_all('tr', recursive=False)
        records = []
        for tr in rows:
            inner_table = tr.find('table', recursive=True)

            if not inner_table:
                continue
            # skip date header segments
            if inner_table.find('span', id='lblRowBreakTitle'):
                continue
            # find row with link
            link_cell = inner_table.find('td', class_='copyReg')
            if not link_cell:
                continue
            a = link_cell.find('a', href=True)
            if not a or 'BidPreview.aspx' not in a['href']:
                continue
            # extract BidID
            m = re.search(r"BidID=(\d+)", a['href'])
            code = m.group(1) if m else ''
            title = a.get_text(strip=True)
            # extract close date
            close_span = inner_table.find('span', id='lblCloseDate')
            if close_span:
                dt = datetime.strptime(close_span.get_text(strip=True), '%m/%d/%Y %I:%M:%S %p')
                end_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                end_str = ''
            # build detail link
            href_match = re.search(r"'([^']+)'", a['href'])
            preview_path = href_match.group(1) if href_match else ''
            base = self.base_url.rsplit('/', 1)[0]
            link = f"{base}/{preview_path}"

            records.append({
                'title':       title,
                'code':        code,
                'end_date': end_str,
                'link':        link,
            })
        return records

    # modifies: self.driver
    # effects: clicks next page if available, returns True if navigated
    def next_page(self):
        try:
            pager = self.driver.find_element(
                By.XPATH,
                "//tr[td/table/tbody/tr/td/a[contains(@href,'__doPostBack')]]"
            )
            next_link = pager.find_element(By.LINK_TEXT, str(self.current_page + 1))
            old_table = self.driver.find_element(By.ID, 'gvResults')
            next_link.click()
            WebDriverWait(self.driver, 10).until(EC.staleness_of(old_table))
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'gvResults'))
            )
            self.current_page += 1
            return True
        except (NoSuchElementException, TimeoutException, WebDriverException):
            return False

    # requires: search(), extract_data(), next_page()
    # effects: orchestrates pagination and filtering, returns list of dicts
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Vermont")
        try:
            if not self.search(**kwargs):
                raise RuntimeError("Search initialization failed")
            self.current_page = 1
            all_records = []
            while True:
                batch = self.extract_data()
                all_records.extend(batch)
                if not self.next_page():
                    break
            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total after filtering: {len(filtered)}")
            return filtered.to_dict('records')
        except Exception as e:
            self.logger.error(f"Vermont scrape failed: {e}", exc_info=True)
            raise
