import logging
from logging.handlers import RotatingFileHandler
import os

LOG_FILE_NAME = "bot.log"
PORT = os.environ.get('PORT', '8005')
OWNER_ID = 6648688093
MSG_EFFECT = 5159385139981059251
SHORT_URL = "arolinks.com"
SHORT_API = "97efe163e07453fe37fcd8a36adb284fb2adca2f"

def LOGGER(name: str, client_name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    formatter = logging.Formatter(
        f"[%(asctime)s - %(levelname)s] - {client_name} - %(name)s - %(message)s",
        datefmt='%d-%b-%y %H:%M:%S'
    )
    file_handler = RotatingFileHandler(LOG_FILE_NAME, maxBytes=50_000_000, backupCount=10)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
