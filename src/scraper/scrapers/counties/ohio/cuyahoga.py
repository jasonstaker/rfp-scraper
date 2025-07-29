# cuyahoga.py
# url: https://ccprod-lm01.cloud.infor.com:1442/lmscm/SourcingSupplier/list/SourcingEvent.OpenForBid?sortOrderName=SourcingEvent.SymbolicKey&fk=SourcingEvent%2810,4080%29&csk.CHP=LMPROC&hasNext=false&menu=EventManagement.BrowseOpenEvents&previousDisabled=true&pageop=load&pagesize=200&csk.SupplierGroup=CUYA&hasPrevious=false&rk=SourcingEvent%28_niu_,_niu_%29&isAscending=true&lk=SourcingEvent%2810,6572%29

import logging
import requests
from datetime import datetime
import pandas as pd

from src.config import COUNTY_RFP_URL_MAP
from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Cuyahoga (OH) open sourcing events via Infor CloudSuite
class CuyahogaScraper(RequestsScraper):

    # effects: initializes with Infor CloudSuite OpenForBid URL and sets up logger & headers
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP["ohio"]["cuyahoga"])
        self.logger = logging.getLogger(__name__)
        
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "x-ssoclienttype": "MSXML",
        })
        
        parts = self.base_url.split("?", 1)
        self.list_base = parts[0]
        self.orig_query = parts[1] if len(parts) > 1 else ""


    # effects: GETs the OpenForBid list; returns parsed JSON
    def search(self, **kwargs):
        try:
            resp = self.session.get(self.base_url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            self.logger.error(f"search HTTP error: {e}", exc_info=False)
            raise SearchTimeoutError("Cuyahoga search HTTP error") from e
        except ValueError as e:
            self.logger.error(f"search JSON decode error: {e}", exc_info=False)
            raise DataExtractionError("Cuyahoga search JSON decode failed") from e


    # requires: response_json from search()
    # effects: extracts list of {code, title, end_date, link} for events with status "Open"
    def extract_data(self, data):
        dv = data.get("dataViewSet")
        if not dv or "data" not in dv:
            raise DataExtractionError("Cuyahoga extract_data missing 'dataViewSet.data'")
        try:
            records = []
            range_key = dv.get("rangeViewKey", "")
            for item in dv["data"]:
                fields = item.get("fields", {})
                
                status = fields.get("_op_DerivedStatusForSupplier_spc_translation_cp_")
                if not status or (status.get("value") != "Open" and status.get("value") != "Amendment in progress"):
                    continue
                
                code = fields.get("SourcingEvent", {}).get("value")
                
                title = fields.get("Name", {}).get("value", "").strip()
                
                raw_close = fields.get("CloseDate", {}).get("value", "").strip()
                if raw_close:
                    dt = datetime.strptime(raw_close[:14], "%Y%m%d%H%M%S")
                    end_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    end_date = ""
                
                resource_id = item.get("resourceId")
                detail_base = self.list_base.replace(
                    "/list/SourcingEvent.OpenForBid",
                    f"/form/{resource_id}.Summary"
                )
                link = f"{detail_base}?{self.orig_query}&action=_open&list={range_key}.OpenForBid&pk={resource_id}"

                records.append({
                    "code": code,
                    "title": title,
                    "end_date": end_date,
                    "link": link,
                })
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Cuyahoga extract_data failed") from e


    # effects: orchestrates search -> extract_data -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Cuyahoga County, OH")
        try:
            data = self.search()
            raw = self.extract_data(data)
            df = pd.DataFrame(raw)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except (SearchTimeoutError, DataExtractionError) as e:
            self.logger.error(f"Cuyahoga scrape failed: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Cuyahoga scrape unexpected error: {e}", exc_info=True)
            raise ScraperError("Cuyahoga scrape failed") from e
