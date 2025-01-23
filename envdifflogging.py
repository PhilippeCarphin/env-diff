import logging
import sys
import os

def configureLogging(format=None, level=logging.DEBUG):
    if format is None:
        name = os.path.basename(sys.argv[0])
        format = "[" + name + " {levelname} - {funcName}()] {message}"

    if sys.stderr.isatty():
        logging.addLevelName( logging.WARNING, f"\033[0;33m{logging.getLevelName(logging.WARNING)}\033[1;0m")
        logging.addLevelName( logging.ERROR,   f"\033[0;31m{logging.getLevelName(logging.ERROR)}\033[1;0m")
        logging.addLevelName( logging.INFO,    f"\033[0;35m{logging.getLevelName(logging.INFO)}\033[1;0m")
        logging.addLevelName( logging.DEBUG,   f"\033[36m{logging.getLevelName(logging.DEBUG)}\033[1;0m")

    logging.basicConfig(format=format, style='{', level=level)
