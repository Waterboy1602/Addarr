import os
import yaml
import i18n
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from commons import checkId, authentication, checkAdmin
from translations import i18n
from config import config

config = config["transmission"]

TSL_LIMIT = 'limited'
TSL_NORMAL = 'normal'

def transmission(update, context):
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

    if not checkAdmin(update):
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
