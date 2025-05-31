# california.py
import logging
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from io import StringIO

import pandas as pd
from bs4 import BeautifulSoup

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

from scraper.config.settings import BUSINESS_UNIT_DICT

class CaliforniaScraper(SeleniumScraper):
    # Scraper for California state RFP portal, parsing the on‑page table
    def __init__(self):
        # configure headless Chrome with minimal logs
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])

        # initialize base scraper with our options
        super().__init__(STATE_RFP_URL_MAP['california'], options=chrome_options)

        # replace driver service to suppress console noise
        try:
            self.driver.quit()
        except:
            pass
        service = Service(log_path=None, service_args=['--silent'])
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        self.logger = logging.getLogger('california')

    def search(self, **kwargs):
        # navigate to page and wait for results table to load
        self.logger.info('navigating to California RFP page')
        self.driver.get(self.base_url)
        # wait until table with id 'datatable-ready' appears
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="datatable-ready"]'))
        )
        # give JS time to populate rows if needed
        time.sleep(2)
    
        return self.driver.page_source

    from scraper.config.settings import BUSINESS_UNIT_DICT

    def extract_data(self, page_source):
        self.logger.debug('parsing HTML table for records')
        try:
            soup = BeautifulSoup(page_source, 'html.parser')
            table = soup.find('table', id='datatable-ready')
            df = pd.read_html(StringIO(str(table)))[0]

            # Prepare a list of links based on department name and event ID
            links = []
            for _, row in df.iterrows():
                department_name = row.iloc[3]  # department column
                event_id = row.iloc[1]         # event ID column
                bu = BUSINESS_UNIT_DICT.get(department_name)
                if bu:
                    url = f"https://caleprocure.ca.gov/event/{bu}/{event_id}"
                else:
                    url = None
                links.append(url)

            # Construct the final mapped DataFrame with links included
            mapped = pd.DataFrame({
                'Label': df.iloc[:, 2],            # Event Name
                'Code': df.iloc[:, 1],             # Event ID
                'End (UTC-7)': df.iloc[:, 4],      # End Date
                'Type': 'RFP',
                'Keyword Hits': '',
                'Link': links
            })
            mapped['Link'] = mapped['Link'].fillna('https://caleprocure.ca.gov/pages/Events-BS3/event-search.aspx')
            return mapped.to_dict('records')

        except Exception as e:
            self.logger.error(f'error parsing HTML table: {e}')
            return []



    def scrape(self, **kwargs):
        # high‑level orchestration: load page, parse, filter
        self.logger.info('starting scrape process')
        try:
            html = self.search(**kwargs)
            records = self.extract_data(html)
            if not records:
                return []
            df = pd.DataFrame(records)
            filtered = filter_by_keywords(df)
            return filtered.to_dict('records')
        except Exception as e:
            self.logger.error(f'scrape failed: {e}')
            return []
        finally:
            self.close()
