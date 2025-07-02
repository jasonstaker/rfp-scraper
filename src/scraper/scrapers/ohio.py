# ohio.py
# url: https://ohiobuys.ohio.gov/page.aspx/en/rfp/request_browse_public

import logging
import os
from urllib.parse import urljoin, urlencode

import pandas as pd
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo
from datetime import datetime

from scraper.core.requests_scraper import RequestsScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic

# a scraper for Ohio RFP data using Requests
class OhioScraper(RequestsScraper):
    # requires: STATE_RFP_URL_MAP contains 'ohio'
    # modifies: self.session
    # effects: initializes scraper with Ohio's RFP browse URL and sets browser-like headers
    def __init__(self):
        base = STATE_RFP_URL_MAP.get("ohio")
        super().__init__(base)
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.base_url,
        })
        # AJAX pagination endpoint
        self.ajax_url = (
            f"{self.base_url.replace('page.aspx', 'ajax.aspx')}"
            "?ivControlUIDsAsync=body:x:grid:upgrid&asyncmodulename=rfp&asyncpagename=request_browse_public"
        )

    # effects: performs GET to load initial page and extract viewstate, generator, CSRFToken, and max page index
    def _init_form(self, html=None):
        if html is None:
            resp = self.session.get(self.base_url, timeout=15)
            resp.raise_for_status()
            html = resp.text
        soup = BeautifulSoup(html, 'html.parser')
        return {
            'VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'],
            'VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'],
            'CSRFToken': soup.find('input', {'name': 'CSRFToken'})['value'],
            'max_page': int(soup.find('input', {'id': 'maxpageindexbody_x_grid_grd'})['value']),
        }

    # requires: valid form_state dict from _init_form
    # effects: sends AJAX POST to retrieve HTML for specified page index
    def _fetch_page(self, form_state, page):
        payload = {
            '__EVENTTARGET': 'body_x_grid_grd',
            '__EVENTARGUMENT': f'Page|{page}',
            '__VIEWSTATE': form_state['VIEWSTATE'],
            '__VIEWSTATEGENERATOR': form_state['VIEWSTATEGENERATOR'],
            'CSRFToken': form_state['CSRFToken'],
            'body_x_selStatusCode_4': 'val',
            'hdnUserValue': ',body_x_selStatusCode_4,body_x_cbRfpPubAward',
            'ajaxrowsiscountedbody_x_grid_grd': 'True',
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'IV-Ajax': 'AjaxPost=true',
            'IV-AjaxControl': 'updatepanel',
            'X-Requested-With': 'XMLHttpRequest',
        }
        resp = self.session.post(self.ajax_url, data=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.text

    # requires: HTML string containing grid table
    # effects: parses RFP rows into standardized record dicts
    def extract_data(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', {'id': 'body_x_grid_grd'})
        if not table:
            self.logger.error('Could not find RFP grid table')
            return []
        records = []
        for tr in table.select('tbody > tr[id^=body_x_grid_grd_tr_]'):
            try:
                tds = tr.find_all('td', recursive=False)
                code = tds[1].get_text(strip=True)
                label = tds[2].get_text(strip=True)
                end_str = tds[5].get_text(strip=True)
                dt_et = datetime.strptime(end_str, '%m/%d/%Y %I:%M:%S %p').replace(
                    tzinfo=ZoneInfo('America/New_York')
                )
                end_norm = parse_date_generic(dt_et.strftime('%Y-%m-%d %H:%M:%S'))
                a = tr.find('a', href=True)
                link = urljoin(self.base_url, a['href'].strip())
                records.append({
                    'Label': label,
                    'Code': code,
                    'End (UTC-7)': end_norm,
                    'Keyword Hits': '',
                    'Link': link,
                })
            except Exception as e:
                self.logger.error(f'Row parse failed: {e}', exc_info=True)
        return records

    # effects: orchestrates full scrape: initial load, search POST, AJAX pagination, parsing, filtering
    def scrape(self, **kwargs):
        self.logger.info('Starting scrape for Ohio with pagination')
        # initialize form and get max pages
        init_html = self.session.get(self.base_url, timeout=15).text
        form_state = self._init_form(init_html)

        # first page via search button
        first_payload = {
            '__EVENTTARGET': 'body:x:prxFilterBar:x:cmdSearchBtn',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': form_state['VIEWSTATE'],
            '__VIEWSTATEGENERATOR': form_state['VIEWSTATEGENERATOR'],
            'CSRFToken': form_state['CSRFToken'],
            'body_x_selStatusCode_4': 'val',
            'hdnUserValue': ',body_x_selStatusCode_4,body_x_cbRfpPubAward',
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        resp = self.session.post(self.base_url, data=first_payload, headers=headers, timeout=30)
        resp.raise_for_status()
        all_records = self.extract_data(resp.text)

        # subsequent AJAX pages
        max_page = form_state['max_page']
        self.logger.info(f'Found {max_page+1} pages; iterating AJAX calls')
        for page in range(1, max_page+1):
            html = self._fetch_page(form_state, page)
            all_records.extend(self.extract_data(html))

        # filter and return
        df = pd.DataFrame(all_records)
        self.logger.info(f'Total raw records before filtering: {len(df)}')
        filtered = filter_by_keywords(df)
        self.logger.info(f'Total records after filtering: {len(filtered)}')
        return filtered.to_dict('records')
