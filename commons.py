import yaml
import logging

import logger
from definitions import CONFIG_PATH

config = yaml.safe_load(open(CONFIG_PATH, encoding="utf8"))

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.commons", logLevel, config.get("logToConsole", False))


def generateServerAddr(app):
    try:
        if config[app]["server"]["ssl"]:
            http = "https://"
        else:
            http = "http://"
        try:
            addr = config[app]["server"]["addr"]
            port = config[app]["server"]["port"]
            return http + addr + ":" + str(port)
        except Exception:
            logger.warn("No ip or port defined.")
    except Exception as e:
        logger.warn(f"Generate of serveraddress failed: {e}.")


def cleanUrl(text):
    url = text.replace(" ", "%20")
    return url


def generateApiQuery(app, endpoint, parameters={}):
    try:
        apikey = config[app]["auth"]["apikey"]
        url = (
            generateServerAddr(app) + "/api/" + str(endpoint) + "?apikey=" + str(apikey)
        )
        # If parameters exist iterate through dict and add parameters to URL.
        if parameters:
            for key, value in parameters.items():
                url += "&" + key + "=" + value
        return cleanUrl(url)  # Clean URL (validate) and return as string
    except Exception as e:
        logger.warn(f"Generate of APIQUERY failed: {e}.")
