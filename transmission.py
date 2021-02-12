import os
import yaml
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from commons import checkId, authentication, checkAdmin
from definitions import LANG_PATH

from config import config

lang = config["language"]
config = config["transmission"]

transcript = yaml.safe_load(open(LANG_PATH, encoding="utf8"))
transcript = transcript[lang]

TSL_LIMIT = 'limited'
TSL_NORMAL = 'normal'

def transmission(update, context):
    if not config["enable"]:
        context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=transcript["Transmission"]["NotEnabled"],
        )
        return ConversationHandler.END

    if not checkId(update):
        context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=transcript["Authorize"]
        )
        return TSL_NORMAL

    if not checkAdmin(update):
        context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=transcript["NotAdmin"],
        )
        return TSL_NORMAL

    keyboard = [[
        InlineKeyboardButton(
            '\U0001F40C '+transcript["Transmission"]["TSL"],
            callback_data=TSL_LIMIT
        ),
        InlineKeyboardButton(
            '\U0001F406 '+transcript["Transmission"]["Normal"],
            callback_data=TSL_NORMAL
        ),
    ]]
    markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        transcript["Transmission"]["Speed"], reply_markup=markup
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
        message = transcript["Transmission"]["ChangedToNormal"]    
    elif choice == TSL_LIMIT:
        command += ' --alt-speed'
        message=transcript["Transmission"]["ChangedToTSL"],
    
    os.system(command)

    context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=message,
        )
    return ConversationHandler.END
