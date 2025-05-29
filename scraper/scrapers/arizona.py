import logging
from io import StringIO
from urllib.parse import parse_qsl, urlencode, urljoin

import pandas as pd
from bs4 import BeautifulSoup

from scraper.core.requests_scraper import RequestsScraper
from scraper.config.settings import FALLBACK_CSRF, STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords


class ArizonaScraper(RequestsScraper):
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["arizona"])
        self.hidden_fields = {}
        self.previous_df = None
        self.current_df = None
        self.logger = logging.getLogger(__name__)

    def _scrape_hidden_fields(self, html_text):
        soup = BeautifulSoup(html_text, "html.parser")
        return {inp["name"]: inp.get("value", "")
                for inp in soup.find_all("input", type="hidden") if inp.get("name")}


    def _build_search_payload(self):
        # build initial post data for search
        data = {**self.hidden_fields}
        data["hdnUserValue"] = "%2Cbody_x_txtRfpAwarded_1"
        data["__LASTFOCUS"] = "body_x_prxFilterBar_x_cmdSearchBtn"
        data["__EVENTTARGET"] = "body:x:prxFilterBar:x:cmdSearchBtn"
        data["__EVENTARGUMENT"] = ""
        data["HTTP_RESOLUTION"] = ""
        data["REQUEST_METHOD"] = "POST"
        data["header:x:prxHeaderLogInfo:x:ContrastModal:chkContrastTheme_radio"] = "true"
        data["header:x:prxHeaderLogInfo:x:ContrastModal:chkContrastTheme"] = "True"
        data["x_headaction"] = ""
        data["x_headloginName"] = ""
        data["header:x:prxHeaderLogInfo:x:ContrastModal:chkPassiveNotification"] = "0"
        data["proxyActionBar:x:txtWflRefuseMessage"] = ""
        data["hdnMandatory"] = "0"
        data["hdnWflAction"] = ""
        data["body:_ctl0"] = ""
        data["body:x:txtQuery"] = ""
        data["body_x_selFamily_text"] = ""
        data["body:x:selFamily"] = ""
        data["body:x:prxFilterBar:x:cmdSearchBtn"] = ""
        data["body:x:prxFilterBar:x:hdnResetFilterUrlbody_x_prxFilterBar_x_cmdRazBtn"] = ""
        data["body_x_selRfptypeCode_text"] = ""
        data["body:x:selRfptypeCode"] = ""
        data["body_x_selStatusCode_1_text"] = ""
        data["body:x:selStatusCode_1"] = ""
        data["body:x:txtRfpBeginDate"] = ""
        data["body:x:txtRfpBeginDatemax"] = ""
        data["body_x_txtRfpAwarded_1_text"] = ""
        data["body:x:txtRfpAwarded_1"] = "False"
        data["body_x_selOrgaLevelOrgaNode_78E9FF04_1_text"] = ""
        data["body:x:selOrgaLevelOrgaNode_78E9FF04_1"] = ""
        tr_checks = [
            "body:x:grid:grd:tr_2884:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_2001:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_1997:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_1971:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_1969:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_1964:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_1955:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_1950:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_1931:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_1927:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_1921:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_1912:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_1910:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_1903:ctrl_txtRfpAwarded=False",
            "body:x:grid:grd:tr_1893:ctrl_txtRfpAwarded=False",
        ]
        for entry in tr_checks:
            key, val = entry.split("=", 1)
            data[key] = val
        data["hdnSortExpressionbody_x_grid_grd"] = ""
        data["hdnSortDirectionbody_x_grid_grd"] = ""
        data["hdnCurrentPageIndexbody_x_grid_grd"] = "0"
        data["hdnRowCountbody_x_grid_grd"] = "100"
        data["maxpageindexbody_x_grid_grd"] = "6"
        data["ajaxrowsiscountedbody_x_grid_grd"] = "True"
        
        # ensure csrf token present
        data["CSRFToken"] = self.hidden_fields.get("CSRFToken", FALLBACK_CSRF)
        self.logger.debug("built search payload")
        return urlencode(data, safe=":/|%")

    def _build_pagination_payload(self, page_num):
        # build post data for specific page number
        focus_idx = page_num - 1
        arg_idx = page_num - 1
        curr_idx = page_num - 2
        data = {
            "__LASTFOCUS": f"body_x_grid_PagerBtn{focus_idx}Page",
            "__EVENTTARGET": "body_x_grid_grd",
            "__EVENTARGUMENT__": f"Page|{arg_idx}",
            **self.hidden_fields
        }
        data["hdnCurrentPageIndexbody_x_grid_grd"] = str(curr_idx)
        extras = {
            "hdnUserValue": "",
            "HTTP_RESOLUTION": "",
            "REQUEST_METHOD": "GET",
            "header:x:prxHeaderLogInfo:x:ContrastModal:chkContrastTheme_radio": "true",
            "header:x:prxHeaderLogInfo:x:ContrastModal:chkContrastTheme": "True",
            "x_headaction": "",
            "x_headloginName": "",
            "header:x:prxHeaderLogInfo:x:ContrastModal:chkPassiveNotification": "0",
            "proxyActionBar:x:txtWflRefuseMessage": "",
            "hdnMandatory": "0",
            "hdnWflAction": "",
            "body:_ctl0": "",
            "body:x:txtQuery": "",
            "body_x_selFamily_text": "",
            "body:x:selFamily": "",
            "body:x:prxFilterBar:x:hdnResetFilterUrlbody_x_prxFilterBar_x_cmdRazBtn": "",
            "body_x_selRfptypeCode_text": "",
            "body:x:selRfptypeCode": "",
            "body_x_selStatusCode_1_text": "",
            "body:x:selStatusCode_1": "",
            "body:x:txtRfpBeginDate": "",
            "body:x:txtRfpBeginDatemax": "",
            "body_x_txtRfpAwarded_1_text": "",
            "body:x:txtRfpAwarded_1": "False",
            "body_x_selOrgaLevelOrgaNode_78E9FF04_1_text": "",
            "body:x:selOrgaLevelOrgaNode_78E9FF04_1": "",
            "hdnSortExpressionbody_x_grid_grd": "",
            "hdnSortDirectionbody_x_grid_grd": "",
            "hdnRowCountbody_x_grid_grd": self.hidden_fields.get("hdnRowCountbody_x_grid_grd", ""),
            "maxpageindexbody_x_grid_grd": self.hidden_fields.get("maxpageindexbody_x_grid_grd", ""),
            "ajaxrowsiscountedbody_x_grid_grd": self.hidden_fields.get("ajaxrowsiscountedbody_x_grid_grd", "False"),
        }
        # ensure csrf token present
        data["CSRFToken"] = self.hidden_fields.get("CSRFToken", FALLBACK_CSRF)
        return urlencode(data, safe=":/|%")

    def search(self, **kwargs):
        # start initial get/post search flow
        self.logger.info("starting search for arizona rfps")
        resp = self.session.get(self.base_url)
        if resp.status_code != 200:
            self.logger.error(f"get failed: {resp.status_code}")
            return None

        self.hidden_fields = self._scrape_hidden_fields(resp.text)
        payload = self._build_search_payload()
        self.current_response = self.session.post(self.base_url, data=dict(parse_qsl(payload)))

        if self.current_response.status_code != 200:
            self.logger.error(f"post failed: {self.current_response.status_code}")
            return None

        self.hidden_fields = self._scrape_hidden_fields(self.current_response.text)
        return self.current_response.text

    def next_page(self):
        # request next page until no more
        if not self.current_response:
            return None
        page = getattr(self, "page_num", 2)
        payload = self._build_pagination_payload(page)
        resp = self.session.post(self.base_url, data=dict(parse_qsl(payload)))
        if resp.status_code != 200:
            return None

        new_hidden = self._scrape_hidden_fields(resp.text)
        if "__VIEWSTATE" not in new_hidden:
            return None

        self.hidden_fields = new_hidden
        self.current_response = resp
        self.page_num = page + 1
        return resp.text

    def extract_data(self, page_content):
        self.logger.debug("extracting data from page")
        try:
            # table parse
            tables = pd.read_html(StringIO(page_content))
            if len(tables) <= 4:
                self.logger.error("unexpected table count, saving debug html")
                with open(f"debug_page_{getattr(self, 'page_num', 1)}.html", "w", encoding="utf-8") as f:
                    f.write(page_content)
                return []
            df = tables[4].reset_index(drop=True)

            # BeautifulSoup locates the table
            soup = BeautifulSoup(page_content, "html.parser")
            tbl = soup.find("table", id="body_x_grid_grd")
            rows = tbl.select("tbody > tr")

            # extract href from the <a> in the first <td> of each row
            links = []
            for tr in rows:
                first_td = tr.find_all("td", recursive=False)[0]
                a = first_td.find("a", href=True)
                href = a["href"] if a else None
                # make absolute if needed
                if href and not href.startswith("http"):
                    href = urljoin(self.base_url, href)
                links.append(href)

            # check
            if len(links) < len(df):
                links += [None] * (len(df) - len(links))
            elif len(links) > len(df):
                links = links[: len(df)]

            # insert
            df["Link"] = links

            self.current_df = df
            self.logger.info(f"found {len(df)} records (with Link column)")
            return df.to_dict("records")

        except Exception as e:
            self.logger.error(f"error extracting data: {e}")
            return []


    def scrape(self, **kwargs):
        # orchestrate full scrape with pagination and filtering
        self.logger.info("starting scrape process")
        results = []

        try:
            page = self.search(**kwargs)
            if page:
                results.extend(self.extract_data(page))
                self.previous_df = self.current_df

            # loop through pages until repetition or end
            while page:
                page = self.next_page()
                if not page:
                    break
                results.extend(self.extract_data(page))
                if self.current_df.equals(self.previous_df):
                    self.logger.info("identical page detected, stopping")
                    break
                self.previous_df = self.current_df

            # filter by keywords before returning
            self.logger.info(f"records before filter: {len(results)}")
            df_all = pd.DataFrame(results)
            filtered = filter_by_keywords(df_all)
            self.logger.info(f"records after filter: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"scrape failed: {e}")
            return []

        finally:
            self.close()