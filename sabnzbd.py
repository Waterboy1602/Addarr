import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from commons import authentication, checkAllowed, checkId, generateApiQuery
from config import config
from translations import i18n
import logging
import logger

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.radarr", logLevel, config.get("logToConsole", False))

config = config["sabnzbd"]

SABNZBD_SPEED_LIMIT_25 = '25'
SABNZBD_SPEED_LIMIT_50 = '50'
SABNZBD_SPEED_LIMIT_100 = '100'


def sabnzbd(update, context):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        return ConversationHandler.END
        
    if not config["enable"]:
        context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.Sabnzbd.NotEnabled"),
        )
        return ConversationHandler.END

    if not checkId(update):
        context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Authorize")
        )
        return SABNZBD_SPEED_LIMIT_100

    if not checkAllowed(update, "admin"):
        context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.NotAdmin"),
        )
        return SABNZBD_SPEED_LIMIT_100

    keyboard = [[
        InlineKeyboardButton(
            '\U0001F40C ' + i18n.t("addarr.Sabnzbd.Limit25"),
            callback_data=SABNZBD_SPEED_LIMIT_25
        ),
        InlineKeyboardButton(
            '\U0001F40E ' + i18n.t("addarr.Sabnzbd.Limit50"),
            callback_data=SABNZBD_SPEED_LIMIT_50
        ),
        InlineKeyboardButton(
            '\U0001F406 ' + i18n.t("addarr.Sabnzbd.Limit100"),
            callback_data=SABNZBD_SPEED_LIMIT_100
        ),
    ]]
    markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        i18n.t("addarr.Sabnzbd.Speed"), reply_markup=markup
    )
    return SABNZBD_SPEED_LIMIT_100


def changeSpeedSabnzbd(update, context):
    if not checkId(update):
        if (
                authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END

    choice = update.callback_query.data

    url = generateApiQuery("sabnzbd", "",
                           {'output': 'json', 'mode': 'config', 'name': 'speedlimit', 'value': choice})

    req = requests.get(url)
    message = None
    if req.status_code == 200:
        if choice == SABNZBD_SPEED_LIMIT_100:
            message = i18n.t("addarr.Sabnzbd.ChangedTo100")
        elif choice == SABNZBD_SPEED_LIMIT_50:
            message = i18n.t("addarr.Sabnzbd.ChangedTo50")
        elif choice == SABNZBD_SPEED_LIMIT_25:
            message = i18n.t("addarr.Sabnzbd.ChangedTo25")

    else:
        message = i18n.t("addarr.Sabnzbd.Error")

    context.bot.send_message(
        chat_id=update.effective_message.chat_id,
        text=message,
    )

    return ConversationHandler.END
