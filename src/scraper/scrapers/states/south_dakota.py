# south_dakota.py
# url: https://postingboard.esmsolutions.com/3444a404-3818-494f-84c5-2a850acd7779/events

import logging
from datetime import datetime
from urllib.parse import urljoin

import pandas as pd

from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.config.settings import STATE_RFP_URL_MAP

# a scraper for South Dakota RFP data using Requests
class SouthDakotaScraper(RequestsScraper):
    # modifies: self
    # effects: initializes scraper with SD posting board API URL and configures session
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["south dakota"])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*"
        })

    # effects: fetches all events in one request by using a large recordsPerPage
    def search(self, **kwargs):
        # use a high recordsPerPage to retrieve all in one go
        params = {
            "pageNo": 0,
            "recordsPerPage": kwargs.get("recordsPerPage", 1000),
            "browserGlobalTimeZoneNameId": "Pacific Daylight Time",
            "browserGlobalTimeZoneName": "America/Los_Angeles",
            "browserOffset": "-07:00:00",
        }
        try:
            resp = self.session.get(self.base_url, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise

    # requires: response_json is dict with 'data'
    # effects: extracts event records into standardized list of dicts
    def extract_data(self, response_json):
        if not response_json or "data" not in response_json:
            self.logger.error("Invalid JSON content in extract_data")
            raise RuntimeError("No data field in JSON")
        
        board_id = '3444a404-3818-494f-84c5-2a850acd7779'

        records = []
        base_detail = (
            f"https://postingboard.esmsolutions.com/"
            f"{board_id}/eventDetail/"
        )

        for rec in response_json["data"]:
            try:
                title = rec.get("eventName", "").strip()
                code = rec.get("id", "").strip()
                
                end_str = rec.get("eventDueDate", "").strip()

                try:
                    dt = datetime.fromisoformat(end_str)
                    end_fmt = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    end_fmt = end_str

                eventId = rec.get("eventId", "").strip()
                link = urljoin(base_detail, eventId)

                records.append({
                    "title": title,
                    "code": code,
                    "end_date": end_fmt,
                    "link": link,
                })
            except Exception as e:
                self.logger.error(f"Error parsing record: {e}", exc_info=False)
                continue
        return records

    # effects: orchestrates full scrape: search -> extract_data -> filter -> return
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for South Dakota")
        try:
            json_data = self.search(**kwargs)
            raw_records = self.extract_data(json_data)
            df = pd.DataFrame(raw_records)
            self.logger.info(f"Total raw records: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except Exception as e:
            self.logger.error(f"South Dakota scrape failed: {e}", exc_info=True)
            raise
