import logging
import os
from logging.handlers import RotatingFileHandler


LOG_DIR = "logs"

os.makedirs(
    LOG_DIR,
    exist_ok=True
)


LOG_FILE = os.path.join(
    LOG_DIR,
    "app.log"
)


def setup_logging():

    logger = logging.getLogger()

    logger.setLevel(
        logging.INFO
    )


    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )


    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )


    file_handler.setFormatter(
        formatter
    )


    logger.addHandler(
        file_handler
    )


    console_handler = logging.StreamHandler()

    console_handler.setFormatter(
        formatter
    )


    logger.addHandler(
        console_handler
    )


# ADD THIS
logger = logging.getLogger(__name__)