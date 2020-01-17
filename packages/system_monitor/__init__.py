import logging
from .constants import APP_NAME


__version__ = '0.0.1'

# create logger
logging.basicConfig()
logger = logging.Logger(APP_NAME, logging.INFO)
