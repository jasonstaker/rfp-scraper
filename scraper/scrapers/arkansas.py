# arkansas.py
import logging
from bs4 import BeautifulSoup
import pandas as pd

from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.core.requests_scraper import RequestsScraper


class ArkansasScraper(RequestsScraper):
    # scraper for Arkansas open bids (ARBuy)
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP['arkansas'])
        self.logger = logging.getLogger(__name__)

    def search(self, **kwargs):
        # initial GET request to fetch open solicitations
        self.logger.info('fetching Arkansas open bids')
        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()
            self.current_response = response.text
            return self.current_response
        except Exception as e:
            self.logger.error(f'search failed: {e}')
            return None

    def extract_data(self, html):
        self.logger.info('parsing ARBuy results table')
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', {'role': 'grid'})
        if not table:
            self.logger.error('results table not found')
            return []

        records = []
        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) < 4:
                continue

            # extract values from cells
            link_tag = cols[0].find('a')
            if not link_tag:
                continue

            code = link_tag.text.strip()
            link = link_tag.get('href')
            label = cols[6].get_text(strip=True)
            end = cols[7].get_text(strip=True)

            full_link = f"https://arbuy.arkansas.gov{link}" if link.startswith('/') else link

            records.append({
                'Label': label,
                'Code': code,
                'End (UTC-7)': end,
                'Keyword Hits': '',
                'Link': full_link
            })

        self.logger.info(f'parsed {len(records)} raw records')
        return records

    def scrape(self, **kwargs):
        # orchestrate search, extraction, and filtering
        self.logger.info('starting Arkansas scrape')
        try:
            html = self.search(**kwargs)
            raw_records = self.extract_data(html)
            df = pd.DataFrame(raw_records)
            self.logger.info(f'total records before filter: {len(df)}')
            filtered = filter_by_keywords(df)
            self.logger.info(f'total records after filter: {len(filtered)}')
            return filtered.to_dict('records')

        except Exception as e:
            self.logger.error(f'scrape failed: {e}')
            return []
        finally:
            self.close()
