# utils/logger.py
"""Application-wide logging setup."""

import logging


def setup_logger():
    """
    Sets up application-wide logging.

    Logs to both the console and a file called ambient_ai.log.
    Format: [TIMESTAMP] [LEVEL] [MODULE]: message
    """
    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(),                          # Print to console
            logging.FileHandler("ambient_ai.log", mode="a"),  # Write to log file
        ],
    )
