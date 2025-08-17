# common/logging_setup.py
import logging
import os
from datetime import datetime

def setup_logging(log_dir: str = "logs"):
    """
    Sets up a centralized logger for the application.
    """
    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(
        log_dir, f"app_log_{datetime.now().strftime('%Y%m%d')}.log"
    )

    log_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s"
    )

    logger = logging.getLogger()
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_filename, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    # Quieten noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured. Console: INFO, File: DEBUG -> '{log_filename}'")