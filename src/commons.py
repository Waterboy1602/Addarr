import logging
import math
from telegram.ext import ConversationHandler
import logger
from config import config
from definitions import ADMIN_PATH, CHATID_PATH, ALLOWLIST_PATH
from translations import i18n

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.commons", logLevel, config.get("logToConsole", False))

_current_label = None

# Sets the global label that can be accessed within other functions
def setLabel(label: str):
    global _current_label
    _current_label = label

def getLabel() -> str:
    global _current_label
    return _current_label

def generateServerAddr(app):
    try:
        global _current_label
        if _current_label is None:
            logger.warning("Label is not set. Call setLabel() first.")
            return ""
    
        instances = config[app]
    
        for instance in instances:
            if instance["label"] == _current_label:
                try:
                    if instance["server"]["ssl"]:
                        http = "https://"
                    else:
                        http = "http://"
                    
                    addr = instance["server"]["addr"]
                    port = instance["server"]["port"]
                    path = instance["server"]["path"]
                    
                    return f"{http}{addr}:{port}{path}"

                except KeyError as e:
                    logger.warning(f"Missing key {e} in configuration for {_current_label} instance.")
                except Exception as e:
                    logger.warning(f"Failed to generate server address for {_current_label}: {e}")
        
        logger.warning(f"{app.capitalize()} instance with label '{_current_label}' not found.")

    except Exception as e:
        logger.warning(f"Generate server address failed: {e}.")

def cleanUrl(text):
    url = text.replace(" ", "%20")
    return url


def generateApiQuery(app, endpoint, parameters={}):
    try:
        global _current_label
        if _current_label is None:
            logger.warning("Label is not set. Call setLabel() first.")
            return ""
        
        instances = config[app]
        for instance in instances:
            if instance["label"] == _current_label:
                apikey = instance["auth"]["apikey"]
        url = (
            generateServerAddr(app) + "api/v3/" + str(endpoint) + "?apikey=" + str(apikey)
        )
        # If parameters exist iterate through dict and add parameters to URL.
        if parameters:
            for key, value in parameters.items():
                url += "&" + key + "=" + value
        return cleanUrl(url)  # Clean URL (validate) and return as string
    except Exception as e:
        logger.warning(f"Generate of APIQUERY failed: {e}.")


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
            chatId = line.strip("\n").split(" - ")[0]
            if chatId == str(update.effective_message.chat_id):
                authorize = True
        file.close()
        if authorize:
            return True
        else:
            return False


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
                text=i18n.t("addarr.Chatid already allowed"),
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
                        text=i18n.t("addarr.Chatid added"),
                    )
                    file.close()
                    return "added"
            else:
                logger.warning(
                    f"Failed authentication attempt by [{update.message.from_user.username}]. Password entered: [{password}]"
                )
                await context.bot.send_message(
                    chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Wrong password")
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
    admin = False
    user = update.effective_user
    with open(path, "r") as file:
        for line in file:
            chatId = line.strip("\n").split(" - ")[0]
            if chatId == str(user["username"]) or chatId == str(user["id"]):
                admin = True
        file.close()
        if admin:
            return True
        else:
            return False


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
