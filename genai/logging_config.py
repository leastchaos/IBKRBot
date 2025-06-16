import logging
from datetime import datetime

def setup_logging():
    """
    Configures the root logger for the application.
    - Sends INFO and higher level messages to the console.
    - Sends DEBUG and higher level messages to a daily log file.
    """
    # Create a filename for the log file with the current date
    log_filename = f"automation_log_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Define the format for the log messages
    log_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s'
    )
    
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set the lowest level to capture all messages

    # --- Console Handler ---
    # This handler prints INFO and higher messages to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    # --- File Handler ---
    # This handler writes DEBUG and higher messages to a file
    file_handler = logging.FileHandler(log_filename, mode='a', encoding='utf-8') # 'a' for append
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    print(f"Logging configured. Console level: INFO, File level: DEBUG -> '{log_filename}'")