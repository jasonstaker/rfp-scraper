# colorado.py
import logging
import time
from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import convert_to_pst


class ColoradoScraper(SeleniumScraper):
    # scraper for Colorado published solicitations
    def __init__(self):
        # configure headless Chrome with fixed viewport, UA, and minimal logs
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

        super().__init__('https://prd.co.cgiadvantage.com/PRDVSS1X1/Advantage4', options=chrome_options)
        self.logger = logging.getLogger(__name__)

    def search(self, **kwargs):
        # navigate to portal and click “View Published Solicitations”
        self.logger.info('navigating to Colorado RFP portal')
        self.driver.get(self.base_url)

        try:
            # use data-qa attribute for robust locator
            button_locator = (By.XPATH,
                "//div[@data-qa='vss.page.VAXXX03153.carouselView.carousel.solicitations']"
            )
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable(button_locator)
            ).click()
            self.logger.info("clicked 'View Published Solicitations'")

            # wait for the solicitations table
            table_locator = (By.ID, 'vsspageVVSSX10019gridView1group1cardGridgrid1')
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located(table_locator)
            )
            time.sleep(1)
            self.logger.info('solicitations table loaded')
            return self.driver.page_source

        except Exception as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            return None

    def extract_data(self, page_source):
        # parse the HTML table into raw records
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
            # expect at least 5 columns: selector, _, label, link cell, date cell
            if len(cols) < 5:
                continue

            label = cols[1].get_text(strip=True)
            anchor = cols[3].find('a', href=True)
            if not anchor:
                continue

            code = anchor.get_text(strip=True)
            link = anchor['href']

            # convert raw date string into PST
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
        # orchestrate search, extract, and filter
        self.logger.info('starting Colorado scrape')
        try:
            page = self.search(**kwargs)
            if not page:
                return []

            records = self.extract_data(page)

            # (Pagination can be added here later)

            df = pd.DataFrame(records)
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
