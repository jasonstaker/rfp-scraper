# logging_config.py
import logging
from logging.handlers import RotatingFileHandler
from logging import Formatter

# a custom logging formatter that adjusts logger names for better readability
class CustomFormatter(Formatter):
    
    # requires: nothing
    # modifies: record.name
    # effects: formats the log record by adjusting logger names and returns the formatted string
    def format(self, record):
        if record.name == 'root':
            record.name = '[main]'
        elif record.name.startswith('scraper.scrapers.') or record.name.startswith('scraper.exporters.'):
            file_name = record.name.split('.')[-1]
            record.name = f'[{file_name}]'
        return super().format(record)


# requires: log_file is a string or Path object specifying the log file path
# modifies: the logging configuration
# effects: sets up logging to write to log_file with a custom formatter and handles log rotation when file exceeds a given size
def configure_logging(
    log_file,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5
):
    handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )

    formatter = CustomFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('WDM').setLevel(logging.WARNING)
