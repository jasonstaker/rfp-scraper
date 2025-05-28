# california.py
# suppress tensorflow logs
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# silence unwanted logger noise
import logging
logging.getLogger('WDM').setLevel(logging.ERROR)
logging.getLogger('selenium').setLevel(logging.ERROR)

# standard imports
import time
import glob
import shutil
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.exporters.excel_exporter import export
from scraper.utils.data_utils import filter_by_keywords


class CaliforniaScraper(SeleniumScraper):
    # scraper for california state rfp site
    def __init__(self):
        # setup headless chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])

        # download directory
        temp_dir = r'C:\Users\jason\vscode\rfp-scraper\temp'
        os.makedirs(temp_dir, exist_ok=True)
        chrome_options.add_experimental_option('prefs', {
            'download.default_directory': temp_dir,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': True
        })

        super().__init__(STATE_RFP_URL_MAP['california'], options=chrome_options)

        # replace driver with silent service
        try:
            self.driver.quit()
        except:
            pass
        service = Service(log_path=os.devnull, service_args=['--silent'])
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        self.logger = logging.getLogger('california')
        self.temp_dir = temp_dir
        self.output_dir = r'C:\Users\jason\vscode\rfp-scraper\output'

    def search(self, **kwargs):
        # clear temp directory
        for f in glob.glob(os.path.join(self.temp_dir, '*')):
            try:
                os.remove(f)
            except:
                pass

        # navigate and export
        self.driver.get(self.base_url)
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="searchForm"]/section[2]'))
        )
        export_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="RESP_INQA_HD_VW_GR$hexcel$0"]'))
        )
        export_button.click()
        time.sleep(2)

        # handle download
        original = self.driver.current_window_handle
        download_button = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="downloadButton"]'))
        )
        download_button.click()
        time.sleep(2)

        if len(self.driver.window_handles) > 1:
            for w in self.driver.window_handles:
                if w != original:
                    self.driver.switch_to.window(w)
                    self.driver.close()
            self.driver.switch_to.window(original)

        return self._wait_for_download()

    def _wait_for_download(self, timeout=60):
        # wait for file to appear
        start = time.time()
        downloads = os.path.expanduser('~/Downloads')
        while time.time() - start < timeout:
            temp_files = glob.glob(os.path.join(self.temp_dir, '*.csv')) + \
                         glob.glob(os.path.join(self.temp_dir, '*.xlsx')) + \
                         glob.glob(os.path.join(self.temp_dir, '*.xls'))
            if temp_files:
                return max(temp_files, key=os.path.getctime)

            download_files = glob.glob(os.path.join(downloads, '*.csv')) + \
                             glob.glob(os.path.join(downloads, '*.xlsx')) + \
                             glob.glob(os.path.join(downloads, '*.xls'))
            if download_files:
                latest = max(download_files, key=os.path.getctime)
                dest = os.path.join(self.temp_dir, os.path.basename(latest))
                shutil.move(latest, dest)
                return dest

            time.sleep(1)
        self.logger.error('download file not found')
        return None

    def extract_data(self, file_path):
        # read file into dataframe
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, encoding='utf-8-sig')
        else:
            try:
                df = pd.read_excel(file_path, engine='xlrd')
            except:
                df = pd.read_html(file_path)[0]

        # map to standard schema
        mapped = pd.DataFrame({
            'Label': df.get('Event Name', ''),
            'Code': df.get('Event ID', ''),
            'End (UTC-7)': df.get('End Date', ''),
            'Type': df.get('Type', 'RFP'),
            'Keyword Hits': ''
        })
        return mapped.to_dict('records')

    def scrape(self, **kwargs):
        start = time.time()
        file_path = None
        try:
            file_path = self.search(**kwargs)
            records = self.extract_data(file_path) if file_path else []
            if records:
                df = pd.DataFrame(records)
                filtered = filter_by_keywords(df)
                if not filtered.empty:
                    return filtered
        except Exception as e:
            self.logger.error(f'Scraping failed: {e}')
        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            self.close()
            elapsed = time.time() - start
            self.logger.info(f'Time taken scraping {elapsed:.1f}s')
        return []
