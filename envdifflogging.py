import logging
import sys

FORMAT = "[{levelname:20} ({asctime}) {process}:{filename}:{lineno} - {funcName}()] {message}"

def configureLogging(format=FORMAT, level=logging.DEBUG):

    if sys.stderr.isatty():
        logging.addLevelName( logging.WARNING, f"\033[0;33m{logging.getLevelName(logging.WARNING)}\033[1;0m")
        logging.addLevelName( logging.ERROR,   f"\033[0;31m{logging.getLevelName(logging.ERROR)}\033[1;0m")
        logging.addLevelName( logging.INFO,    f"\033[0;35m{logging.getLevelName(logging.INFO)}\033[1;0m")
        logging.addLevelName( logging.DEBUG,   f"\033[1;00m{logging.getLevelName(logging.DEBUG)}\033[1;0m")

    logger = logging.getLogger(__name__)
    logging.basicConfig(format=FORMAT, style='{')
    logger.setLevel(level)
