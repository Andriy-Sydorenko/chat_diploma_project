import logging
import sys

from colorlog import ColoredFormatter

logger = logging.getLogger("diploma_project")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)

formatter = ColoredFormatter(
    "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    },
)

handler.setFormatter(formatter)
logger.addHandler(handler)
