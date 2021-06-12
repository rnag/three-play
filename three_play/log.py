import logging
from logging import getLogger

from .constants import LOG_LEVEL


def get_file_logger(filename: str, name=None, level=logging.INFO,
                    fmt='%(asctime)s - %(levelname)s - %(message)s'):

    logger = logging.getLogger(name or __file__)

    handler = logging.FileHandler(filename)
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(level)

    return logger


LOG = getLogger('three_play')
LOG.setLevel(LOG_LEVEL)
