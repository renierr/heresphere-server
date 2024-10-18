from loguru import logger
import sys

DEBUG = 1
log_level = 'DEBUG' if DEBUG else 'INFO'

logger.remove()
logger.add(sys.stdout, level=log_level)

def get_logger():
    return logger