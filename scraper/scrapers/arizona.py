# arizona.py
import logging
import json
from io import StringIO
from urllib.parse import parse_qsl, urlencode, urljoin

import pandas as pd
from bs4 import BeautifulSoup

from scraper.core.requests_scraper import RequestsScraper
from scraper.config.settings import FALLBACK_CSRF, STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords


class ArizonaScraper(RequestsScraper):
    # scraper for Arizona state RFP portal, parsing html table rows
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP['arizona'])
        self.hidden_fields = {}
        self.previous_df = None
        self.current_df = None
        self.logger = logging.getLogger(__name__)

    def _scrape_hidden_fields(self, html_text):
        # extract hidden input values for post payloads
        soup = BeautifulSoup(html_text, 'html.parser')
        return {inp['name']: inp.get('value', '')
                for inp in soup.find_all('input', type='hidden') if inp.get('name')}

    def _build_search_payload(self):
        # construct form data for initial search request
        data = {**self.hidden_fields}
        data.update({
            'hdnUserValue': '%2Cbody_x_txtRfpAwarded_1',
            '__LASTFOCUS': 'body_x_prxFilterBar_x_cmdSearchBtn',
            '__EVENTTARGET': 'body:x:prxFilterBar:x:cmdSearchBtn',
            'REQUEST_METHOD': 'POST',
            'body:x:txtRfpAwarded_1': 'False',
            'hdnRowCountbody_x_grid_grd': '100',
            'maxpageindexbody_x_grid_grd': '6',
            'ajaxrowsiscountedbody_x_grid_grd': 'True',
            'CSRFToken': self.hidden_fields.get('CSRFToken', FALLBACK_CSRF)
        })
        self.logger.debug('built search payload')
        return urlencode(data, safe=':/|%')

    def _build_pagination_payload(self, page_num):
        # construct form data for next page request
        focus = page_num - 1
        prev = page_num - 2
        data = {
            '__LASTFOCUS': f'body_x_grid_PagerBtn{focus}Page',
            '__EVENTTARGET': 'body_x_grid_grd',
            '__EVENTARGUMENT': f'Page|{focus}',
            **self.hidden_fields,
            'hdnCurrentPageIndexbody_x_grid_grd': str(prev),
            'CSRFToken': self.hidden_fields.get('CSRFToken', FALLBACK_CSRF)
        }
        return urlencode(data, safe=':/|%')

    def search(self, **kwargs):
        # load initial page and scrape hidden form state
        self.logger.info('starting search for arizona rfps')
        resp = self.session.get(self.base_url)
        if resp.status_code != 200:
            self.logger.error(f'get failed: {resp.status_code}')
            return None

        self.hidden_fields = self._scrape_hidden_fields(resp.text)
        payload = self._build_search_payload()
        resp = self.session.post(self.base_url, data=dict(parse_qsl(payload)))
        if resp.status_code != 200:
            self.logger.error(f'post failed: {resp.status_code}')
            return None

        self.hidden_fields = self._scrape_hidden_fields(resp.text)
        return resp.text

    def next_page(self):
        # request next page until no more data
        if not self.current_response:
            return None
        page = getattr(self, 'page_num', 2)
        payload = self._build_pagination_payload(page)
        resp = self.session.post(self.base_url, data=dict(parse_qsl(payload)))
        if resp.status_code != 200:
            return None

        new_hidden = self._scrape_hidden_fields(resp.text)
        if '__VIEWSTATE' not in new_hidden:
            return None

        self.hidden_fields = new_hidden
        self.current_response = resp
        self.page_num = page + 1
        return resp.text

    def extract_data(self, page_content):
        # parse html table into dataframe and extract links
        try:
            tables = pd.read_html(StringIO(page_content))
            df = tables[4]
            soup = BeautifulSoup(page_content, 'html.parser')
            tbl = soup.find('table', id='body_x_grid_grd')
            rows = tbl.select('tbody > tr')

            links = []
            for tr in rows:
                a = tr.find_all('td', recursive=False)[0].find('a', href=True)
                href = a['href'] if a else None
                if href and not href.startswith('http'):
                    href = urljoin(self.base_url, href)
                links.append(href)

            df['Link'] = links
            self.current_df = df
            self.logger.info(f'found {len(df)} records (with Link column)')
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f'error extracting data: {e}')
            return []

    def scrape(self, **kwargs):
        # search, paginate, dedupe, filter
        self.logger.info('starting scrape process')
        results = []
        try:
            page = self.search(**kwargs)
            if page:
                results.extend(self.extract_data(page))
                self.previous_df = self.current_df

            while page:
                page = self.next_page()
                if not page:
                    break
                results.extend(self.extract_data(page))
                if self.current_df.equals(self.previous_df):
                    self.logger.info('identical page detected, stopping')
                    break
                self.previous_df = self.current_df

            self.logger.info(f'records before filter: {len(results)}')
            df = pd.DataFrame(results)
            filtered = filter_by_keywords(df)
            self.logger.info(f'records after filter: {len(filtered)}')
            return filtered.to_dict('records')
        except Exception as e:
            self.logger.error(f'scrape failed: {e}')
            return []
        finally:
            self.close()
