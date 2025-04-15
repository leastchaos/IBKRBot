import logging

def setup_logger(level=logging.INFO) -> logging.Logger:
    """
    Configures the logger to write logs to a file and output to the terminal.
    Returns the configured logger instance.
    """
    logger = logging.getLogger()
    logger.setLevel(level)  # Set the base logger level to DEBUG

    # Create a file handler to write logs to a file
    file_handler = logging.FileHandler("ib_async.log")
    file_handler.setLevel(logging.DEBUG)  # Log everything to the file
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(module)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    # Create a stream handler to output logs to the terminal
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)  # Log everything to the terminal
    stream_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    stream_handler.setFormatter(stream_formatter)

    # Add both handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    logging.getLogger("ib_async").setLevel(logging.WARNING)
    # logging.getLogger("gspread").setLevel(logging.WARNING)
    # logging.getLogger("gspread_dataframe").setLevel(logging.WARNING)
    return logger