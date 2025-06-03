# logging_config.py
import logging
from logging import FileHandler
from logging import Formatter

class CustomFormatter(Formatter):
    def format(self, record):
        if record.name == 'root':
            record.name = '[main]'
        elif record.name.startswith('scraper.scrapers.') or record.name.startswith('scraper.exporters.'):
            file_name = record.name.split('.')[-1]
            record.name = f'[{file_name}]'
        return super().format(record)

def configure_logging(log_file):
    # Configure logging to file with custom formatter
    handler = FileHandler(log_file)
    formatter = CustomFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    # Set levels for specific loggers to suppress unwanted output
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('WDM').setLevel(logging.WARNING)