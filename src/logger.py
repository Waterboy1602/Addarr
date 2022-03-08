#!/usr/bin/env python3

import logging
import os

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
            consoleHandler = logging.StreamHandler()
            consoleHandler.setLevel(logLevel)
            consoleHandler.setFormatter(logFormatter)
            logger.addHandler(consoleHandler)
    return logger
