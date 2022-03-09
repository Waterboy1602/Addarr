import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from commons import authentication, checkAllowed, checkId
from config import config
from translations import i18n
import logging
import logger

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.radarr", logLevel, config.get("logToConsole", False))

config = config["transmission"]

TSL_LIMIT, TSL_NORMAL = range(2)


def transmission(update, context):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END
    
    if not config["enable"]:
        context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.Transmission.NotEnabled"),
        )
        return ConversationHandler.END

    if not checkId(update):
        context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Authorize")
        )
        return TSL_NORMAL

    if config["onlyAdmin"] and not checkAllowed(update, "admin"):
        context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.NotAdmin"),
        )
        return TSL_NORMAL

    keyboard = [[
        InlineKeyboardButton(
            '\U0001F40C '+i18n.t("addarr.Transmission.TSL"),
            callback_data=TSL_LIMIT
        ),
        InlineKeyboardButton(
            '\U0001F406 '+i18n.t("addarr.Transmission.Normal"),
            callback_data=TSL_NORMAL
        ),
    ]]
    markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        i18n.t("addarr.Transmission.Speed"), reply_markup=markup
    )
    return TSL_NORMAL


def changeSpeedTransmission(update, context):
    if not checkId(update):
        if (
            authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END
    
    choice = update.callback_query.data
    command = f"transmission-remote {config['host']}"
    if config["authentication"]:
        command += (
            " --auth "
            + config["username"]
            + ":"
            + config["password"]
        )
    
    message = None
    if choice == TSL_NORMAL:
        command += ' --no-alt-speed'
        message = i18n.t("addarr.Transmission.ChangedToNormal")
    elif choice == TSL_LIMIT:
        command += ' --alt-speed'
        message=i18n.t("addarr.Transmission.ChangedToTSL"),
    
    os.system(command)

    context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=message,
        )
    return ConversationHandler.END
