import logging
import math
import os
import re
from telegram.ext import ConversationHandler
import logger
from config import config
from definitions import ADMIN_PATH, CHATID_PATH, ALLOWLIST_PATH, NOTIFICATIONLIST_PATH
from translations import i18n
import radarr as radarr
import sonarr as sonarr

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.commons", logLevel, config.get("logToConsole", False))

_current_instance = None

# Sets the global label that can be accessed within other functions
def setInstanceName(label: str):
    global _current_instance
    _current_instance = label

def getInstanceName() -> str:
    global _current_instance
    return _current_instance

def getInstance(app):
    instances = config[app]["instances"]
    if _current_instance:
        # Find the instance with the matching label
        for instance in instances:
            if instance["label"] == _current_instance:
                return instance
    else:
        logger.warning('instance not set')
            

def generateServerAddr(app: str):
    try:
        logger.debug(app)
        if not app.lower() == 'radarr' and not app.lower() == 'sonarr':
            logger.debug('generating server address for other service app')
            if config[app]["server"]["ssl"]:
                http = "https://"
            else:
                http = "http://"
            addr = config[app]["server"]["addr"]
            port = config[app]["server"]["port"]
            path = config[app]["server"]["path"]

            return f"{http}{addr}:{port}{path}"
        else:
            logger.debug('generating server address for sonarr/radarr')
            instance = getInstance(app)
            if instance["server"]["ssl"]:
                http = "https://"
            else:
                http = "http://"

            addr = instance["server"]["addr"]
            port = instance["server"]["port"]
            path = instance["server"]["path"]
        
            return f"{http}{addr}:{port}{path}"
       
    except KeyError as e:
        logger.warning(f"Missing key {e} in configuration for {_current_instance} instance.")
            
    except Exception as e:
        logger.warning(f"Failed to generate server address for {_current_instance}: {e}")


def cleanUrl(text):
    url = text.replace(" ", "%20")
    return url


def generateApiQuery(app, endpoint, parameters={}):
    try:
        instance = getInstance(app)
        
        apikey = instance["auth"]["apikey"]
        url = (
            generateServerAddr(app) + "api/v3/" + str(endpoint) + "?apikey=" + str(apikey)
        )
        # If parameters exist iterate through dict and add parameters to URL.
        if parameters:
            for key, value in parameters.items():
                url += "&" + key + "=" + value

        return cleanUrl(url)  # Clean URL (validate) and return as string
    except KeyError as e:
        logger.warning(f"Missing key in configuration: {e}")
    except Exception as e:
        logger.warning(f"Generate of APIQUERY failed: {e}.")


# Check if Id is authenticated
def checkId(update):
    authorize = False
    
    if not os.path.exists(CHATID_PATH):
        with open(CHATID_PATH, "w") as file:
            pass  # Create an empty file
    
    with open(CHATID_PATH, "r") as file:
        firstChar = file.read(1)
        if not firstChar:  # File is empty
            return False

    with open(CHATID_PATH, "r") as file:
        for line in file:
            chatId = line.strip("\n").split(" - ")[0]
            if chatId == str(update.effective_message.chat_id):
                authorize = True

    return authorize

# Check if user has subscribed to notifications
async def checkNotificationSubscribed(chatid):
    onInstance = False
    radarr_instances = config['radarr']['instances']
    sonarr_instances = config['sonarr']['instances']

    for instance in radarr_instances:
        radarr.setInstance(instance["label"])
        setInstanceName(instance["label"])
        onInstance = radarr.notificationProfileExist(chatid)
        
    for instance in sonarr_instances:
        sonarr.setInstance(instance["label"])
        setInstanceName(instance["label"])
        onInstance = sonarr.notificationProfileExist(chatid)

    return onInstance

async def generateProfileName(context, chatid):
    chat = await context.bot.get_chat(chatid)
    if chat.username:
        chatName = str(chat.username)
    elif chat.title:
        chatName = str(chat.title)
    elif chat.last_name and chat.first_name:
        chatName = str(chat.last_name) + str(chat.first_name)
    elif chat.first_name:
        chatName = str(chat.first_name)
    elif chat.last_name:
        chatName = str(chat.last_name)
    else:
        chatName = None

    if chatName is not None:
        return f"{str(chatid)} ({chatName})"
    else:
        return str(chatid)
    

async def authentication(update, context):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END
        
    chatid = update.effective_message.chat_id
    with open(CHATID_PATH, "r") as file:
        if(str(chatid) in file.read()):
            await context.bot.send_message(
                chat_id=update.effective_message.chat_id,
                text=i18n.t("addarr.Authorization.ChatID_Allowed"),
            )
            file.close()
        else:
            file.close()
            password = update.message.text
            # This will remove both /auth and auth from the password string if they are present.
            # It ensures that even if there is no leading slash, it will still be detected and removed.
            if("auth" in password.lower()):
                password = password.lower().replace("/auth", "").replace("auth", "").strip()
            if str(password).strip() == str(config["telegram"]["password"]):
                with open(CHATID_PATH, "a") as file:
                    file.write(await getChatName(context, chatid))
                    await context.bot.send_message(
                        chat_id=update.effective_message.chat_id,
                        text=i18n.t("addarr.Authorization.ChatID_Added"),
                    )
                    file.close()
                    return "added"
            else:
                logger.warning(
                    f"Failed authentication attempt by [{update.message.from_user.username}]. Password entered: [{password}]"
                )
                await context.bot.send_message(
                    chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Authorization.WrongPassword")
                )
                return ConversationHandler.END # This only stops the auth conv, so it goes back to choosing screen


async def getChatName(context, chatid):
    chat = await context.bot.get_chat(chatid)
    if chat.username:
        chatName = str(chat.username)
    elif chat.title:
        chatName = str(chat.title)
    elif chat.last_name and chat.first_name:
        chatName = str(chat.last_name) + str(chat.first_name)
    elif chat.first_name:
        chatName = str(chat.first_name)
    elif chat.last_name:
        chatName = str(chat.last_name)
    else:
        chatName = None

    if chatName is not None:
        chatAuth = str(chatid) + " - " + str(chatName) + "\n"
    else:
        chatAuth = str(chatid) + "\n"
    return chatAuth


# Check if user is an admin or an allowed user
def checkAllowed(update, mode):
    if mode == "admin": 
        path = ADMIN_PATH
    else: 
        path = ALLOWLIST_PATH

    if not os.path.exists(path):
        with open(path, "w") as file:
            pass  # Create an empty file

    admin = False
    user = update.effective_user

    with open(path, "r") as file:
        for line in file:
            chatId = line.strip("\n").split(" - ")[0]
            if chatId == str(user["username"]) or chatId == str(user["id"]):
                admin = True

    return admin


def format_bytes(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def format_long_list_message(list):
    string = ""
    for item in list:
        string += "• " \
                  + item["title"] \
                  + " (" \
                  + str(item["year"]) \
                  + ")" \
                  + "\n" \
                  + "        status: " \
                  + item["status"] \
                  + "\n" \
                  + "        monitored: " \
                  + str(item["monitored"]).lower() \
                  + "\n"

    # max length of a message is 4096 chars
    if len(string) <= 4096:
        return string
    # split string if longer then 4096 chars
    else:
        neededSplits = math.ceil(len(string) / 4096)
        positionNewLine = []
        index = 0
        while index < len(string):  # Get positions of newline, so that the split will happen after a newline
            i = string.find("\n", index)
            if i == -1:
                return positionNewLine
            positionNewLine.append(i)
            index += 1

        # split string at newline closest to maxlength
        stringParts = []
        lastSplit = timesSplit = 0
        i = 4096
        while i > 0 and len(string) > 4096:
            if timesSplit < neededSplits:
                if i + lastSplit in positionNewLine:
                    stringParts.append(string[0:i])
                    string = string[i + 1:]
                    timesSplit += 1
                    lastSplit = i
                    i = 4096
            i -= 1
        stringParts.append(string)
        return stringParts


def getAuthChats():
    chats = []
    with open(CHATID_PATH, "r") as file:
        for line in file:
            chats.append(line.strip("\n"))
        file.close()
    return chats

def getService(context):
    if context.user_data.get("choice").lower() == i18n.t("addarr.General.Series").lower():
        return sonarr
    elif context.user_data.get("choice").lower() == i18n.t("addarr.General.Movie").lower():
        return radarr
    else:
        logger.warning(f"Cannot determine service based on unknown or missing choice: {context.user_data.get('choice')}")
        raise ValueError(
            f"Cannot determine service based on unknown or missing choice: {context.user_data.get('choice')}"
        )
    

def clearUserData(context):
    logger.debug(
        "Removing choice, title, position, paths, and output from context.user_data..."
    )
    for x in [
        x
        for x in ["choice", "title", "position", "output", "paths", "path", "qualityProfiles", "qualityProfile", "update_msg", "title_update_msg", "photo_update_msg", "selectedSeasons", "seasons", "instance",
                  "qbit_msg", "speedtype",]
        if x in context.user_data.keys()
    ]:
        context.user_data.pop(x)
