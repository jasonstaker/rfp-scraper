# bexar.py
# url: https://bexarprod-lm01.cloud.infor.com:1442/lmscm/SourcingSupplier/list/SourcingEvent.OpenForBid?csk.CHP=LMPROC&csk.SupplierGroup=100&fk=SourcingEvent(100,1185)&lk=SourcingEvent(100,1188)&rk=SourcingEvent(_niu_,_niu_)&pageSize=20&pageop=load&menu=EventManagement.BrowseOpenEvents

import logging
import time
from datetime import datetime
import pandas as pd
from src.config import COUNTY_RFP_URL_MAP
from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.core.errors import SearchTimeoutError, DataExtractionError, ScraperError

# a scraper for Bexar County, TX solicitations via the Infor API
class BexarScraper(RequestsScraper):

    # effects: initializes with Bexar County base API URL and sets up logger & headers
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP["texas"]["bexar"])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        })


    # effects: GETs the API with current timestamp param; returns parsed JSON
    def search(self, **kwargs):
        url = f"{self.base_url}&_={int(time.time()*1000)}"
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"search HTTP/JSON error: {e}", exc_info=True)
            raise SearchTimeoutError("Bexar search HTTP error") from e


    # requires: parsed JSON from search()
    # effects: iterates over records, filters open events, converts end_date from yyyymmddHHMMSSXXXX to yyyy-mm-dd, returns list
    def extract_data(self, data):
        try:
            items = data.get("dataViewSet", {}).get("data", [])
            records = []
            for item in items:
                fields = item.get("fields", {})
                status = fields.get("_op_DerivedStatusForSupplier_spc_translation_cp_", {}).get("value", "")
                if status.lower() != "open":
                    continue
                code = fields.get("SourcingEvent", {}).get("value")
                title = fields.get("Name", {}).get("value", "").strip()
                raw_close = fields.get("CloseDate", {}).get("value", "")
                end_date = raw_close
                
                if raw_close.isdigit() and len(raw_close) >= 14:
                    try:
                        ts = raw_close[:14]
                        dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
                        end_date = dt.strftime("%Y-%m-%d")
                    except Exception:
                        pass
                resource = item.get("resourceId")
                detail_url = self.base_url.replace(
                    "list/SourcingEvent.OpenForBid", f"form/{resource}.Summary"
                )
                detail_url += f"?action=_open&list={data['dataViewSet']['rangeViewKey']}.OpenForBid&pk={resource}"
                records.append({
                    "code": str(code),
                    "title": title,
                    "end_date": end_date,
                    "link": detail_url,
                })
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Bexar extract_data failed") from e


    # effects: orchestrates search -> extract_data -> filter -> return records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Bexar County, TX")
        try:
            data = self.search()
            raw = self.extract_data(data)
            df = pd.DataFrame(raw)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except (SearchTimeoutError, DataExtractionError) as e:
            self.logger.error(f"Bexar scrape failed: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Bexar scrape unexpected error: {e}", exc_info=True)
            raise ScraperError("Bexar scrape failed") from e