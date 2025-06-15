#!/usr/bin/env python3

import logging
import logging.handlers
import os
import sys
import io

from definitions import LOG_PATH


def getLogger(loggerName, logLevel, logToConsole):
    logFormatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(loggerName)
    logger.setLevel(logLevel)
    if loggerName == "addarr":
        for h in list(logger.handlers):
            logger.removeHandler(h)
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        fileHandler = logging.handlers.TimedRotatingFileHandler(
            LOG_PATH, when="midnight", interval=1, backupCount=7,
        )
        fileHandler.setLevel(logLevel)
        fileHandler.setFormatter(logFormatter)
        logger.addHandler(fileHandler)
        if logToConsole:
            if sys.stdout.encoding.lower() != "utf-8":
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

            consoleHandler = logging.StreamHandler(sys.stdout)
            consoleHandler.setLevel(logLevel)
            consoleHandler.setFormatter(logFormatter)
            logger.addHandler(consoleHandler)
    return logger
