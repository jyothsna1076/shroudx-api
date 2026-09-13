# logger.py
import logging
from datetime import datetime

# Configure logger
logging.basicConfig(
    filename='audit_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_event(event_type, details):
    """
    Log an event with a custom message.
    """
    message = f"{event_type}: {details}"
    logging.info(message)
