# colorado.py
import logging
import time
from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import convert_to_pst

from scraper.config.settings import STATE_RFP_URL_MAP


class ColoradoScraper(SeleniumScraper):
    # Scraper for Colorado published solicitations
    def __init__(self):
        # Configure headless Chrome (you can uncomment headless if you want)
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/115.0.0.0 Safari/537.36'
        )
        chrome_options.add_argument('--disable-dev-shm-usage')

        super().__init__(STATE_RFP_URL_MAP['colorado'], options=chrome_options)
        self.logger = logging.getLogger(__name__)

    def search(self, **kwargs):
        # Navigate to portal and click “View Published Solicitations”
        self.logger.info('navigating to Colorado RFP portal')
        self.driver.get(self.base_url)

        try:
            button_locator = (
                By.XPATH,
                "//div[@data-qa='vss.page.VAXXX03153.carouselView.carousel.solicitations']"
            )
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable(button_locator)
            ).click()
            self.logger.info("clicked 'View Published Solicitations'")

            # Wait for the solicitations table container to appear
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, 'vsspageVVSSX10019gridView1group1cardGridgrid1'))
            )
            # Give a moment for rows to actually render
            time.sleep(1)
            self.logger.info('solicitations table loaded')
            return True

        except Exception as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            return False

    def extract_data(self, page_source):
        # Parse the HTML table into raw records
        self.logger.info('parsing Colorado solicitations table')
        if not page_source:
            return []

        soup = BeautifulSoup(page_source, 'html.parser')
        table = soup.find('table', id='vsspageVVSSX10019gridView1group1cardGridgrid1')
        if not table:
            self.logger.error('results table not found')
            return []

        tbody = table.find('tbody')
        if not tbody:
            self.logger.error('no <tbody> found in table')
            return []

        records = []
        for row in tbody.find_all('tr'):
            cols = row.find_all('td')
            # Expect at least 5 columns: (0)=expand, (1)=description, (2)=dept/buyer, 
            # (3)=solicitation link cell, (4)=date cell, ...
            if len(cols) < 5:
                continue

            label = cols[1].get_text(strip=True)
            anchor = cols[3].find('a')
            if not anchor:
                continue

            code = anchor.get_text(strip=True)
            link = STATE_RFP_URL_MAP['colorado']

            # Convert raw date string into PST
            date_span = cols[4].find('span')
            raw_date = date_span.get_text(strip=True) if date_span else ''
            try:
                end_pst = convert_to_pst(raw_date)
            except Exception:
                self.logger.warning(f"date conversion failed for '{raw_date}'")
                end_pst = raw_date

            records.append({
                'Label': label,
                'Code': code,
                'End (UTC-7)': end_pst,
                'Keyword Hits': '',
                'Link': link
            })

        self.logger.info(f'parsed {len(records)} raw records')
        return records

    def scrape(self, **kwargs):
        # Orchestrate search, extract, and filter across all pages
        self.logger.info('starting Colorado scrape')
        try:
            if not self.search(**kwargs):
                return []

            all_records = []

            while True:
                # 1) Extract data from the current page
                page_source = self.driver.page_source
                page_records = self.extract_data(page_source)
                all_records.extend(page_records)
                self.logger.info(f'collected {len(page_records)} rows on this page, total so far: {len(all_records)}')

                # 2) Attempt to locate any “Next” button (class="css-1yn6b58")
                next_buttons = self.driver.find_elements(By.CLASS_NAME, "css-1yn6b58")
                if not next_buttons:
                    self.logger.info('“Next” button not found; assuming last page')
                    break

                # 3) From those candidates, pick the first one that’s both displayed & enabled
                next_btn = None
                for btn in next_buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        next_btn = btn
                        break

                if not next_btn:
                    # If none are clickable, we’re done paginating
                    self.logger.info('No clickable “Next” button; stopping pagination')
                    break

                # 4) Before clicking, grab the ID of the first <tr> on this page (if any)
                try:
                    first_row = self.driver.find_element(By.CSS_SELECTOR, "tr[id^='tableDataRow']")
                    old_row_id = first_row.get_attribute("id")
                except NoSuchElementException:
                    old_row_id = None

                # 5) Click “Next”
                next_btn.click()
                self.logger.info('clicked “Next” to advance page')

                # Loop will repeat on the new page

            # 7) After collecting all pages, filter + return
            df = pd.DataFrame(all_records)
            self.logger.info(f'total records before filter: {len(df)}')
            filtered = filter_by_keywords(df)
            self.logger.info(f'total records after filter: {len(filtered)}')
            return filtered.to_dict('records')

        except Exception as e:
            self.logger.error(f'scrape() failed: {e}', exc_info=True)
            return []

        finally:
            self.logger.info('closing browser')
            self.close()
