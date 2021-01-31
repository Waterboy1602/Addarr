import yaml
import logging

import logger

from telegram.ext import ConversationHandler

from definitions import CONFIG_PATH, CHATID_PATH, ADMIN_PATH, LANG_PATH

config = yaml.safe_load(open(CONFIG_PATH, encoding="utf8"))

lang = config["language"]
transcript = yaml.safe_load(open(LANG_PATH, encoding="utf8"))
transcript = transcript[lang]

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
            path = config[app]["server"]["path"]
            return http + addr + ":" + str(port) + path
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
            generateServerAddr(app) + "api/" + str(endpoint) + "?apikey=" + str(apikey)
        )
        # If parameters exist iterate through dict and add parameters to URL.
        if parameters:
            for key, value in parameters.items():
                url += "&" + key + "=" + value
        return cleanUrl(url)  # Clean URL (validate) and return as string
    except Exception as e:
        logger.warn(f"Generate of APIQUERY failed: {e}.")

# Check if Id is authenticated
def checkId(update):
    authorize = False
    with open(CHATID_PATH, "r") as file:
        firstChar = file.read(1)
        if not firstChar:
            return False
        file.close()
    with open(CHATID_PATH, "r") as file:
        for line in file:
            if line.strip("\n") == str(update.effective_message.chat_id):
                authorize = True
        file.close()
        if authorize:
            return True
        else:
            return False

def authentication(update, context):
    chatid = update.effective_message.chat_id
    with open(CHATID_PATH, "r") as file:
        if(str(chatid) in file.read()):
            context.bot.send_message(
                chat_id=update.effective_message.chat_id,
                text=transcript["Chatid already allowed"],
            )
            file.close()
        else:
            file.close()
            password = update.message.text
            if("/auth" in password):
                password = password.replace("/auth ", "")
            if password == config["telegram"]["password"]:
                with open(CHATID_PATH, "a") as file:
                    file.write(str(chatid) + "\n")
                    context.bot.send_message(
                        chat_id=update.effective_message.chat_id,
                        text=transcript["Chatid added"],
                    )
                    file.close()
                    return "added"
            else:
                logger.warning(
                    f"Failed authentication attempt by [{update.message.from_user.username}]. Password entered: [{password}]"
                )
                context.bot.send_message(
                    chat_id=update.effective_message.chat_id, text=transcript["Wrong password"]
                )
                return ConversationHandler.END # This only stops the auth conv, so it goes back to choosing screen

def format_bytes(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
