import os
import yaml
from telegram import ReplyKeyboardMarkup
from telegram.ext import ConversationHandler

from commons import checkId, authentication, checkAdmin
from definitions import CONFIG_PATH, LANG_PATH, ADMIN_PATH

config = yaml.safe_load(open(CONFIG_PATH, encoding="utf8"))
lang = config["language"]
config = config["radarr"]

transcript = yaml.safe_load(open(LANG_PATH, encoding="utf8"))
transcript = transcript[lang]

TSL_NORMAL = 'normal'

def transmission(
    update, context,
):
    if config["enable"]:
        if checkId(update):
            if checkAdmin(update):
                reply_keyboard = [
                    [
                        transcript["Transmission"]["TSL"],
                        transcript["Transmission"]["Normal"],
                    ],
                ]
                markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
                update.message.reply_text(
                    transcript["Transmission"]["Speed"], reply_markup=markup
                )
                return TSL_NORMAL
            else:
                context.bot.send_message(
                    chat_id=update.effective_message.chat_id,
                    text=transcript["NotAdmin"],
                )
                return TSL_NORMAL
        else:
            context.bot.send_message(
                chat_id=update.effective_message.chat_id, text=transcript["Authorize"]
            )
            return TSL_NORMAL
    else:
        context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=transcript["Transmission"]["NotEnabled"],
        )
        return ConversationHandler.END

def changeSpeedTransmission(update, context):
    if not checkId(update):
        if (
            authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END
    else:
        choice = update.message.text
        if choice == transcript["Transmission"]["TSL"]:
            auth = None
            if config["authentication"]:
                auth = (
                    " --auth "
                    + config["username"]
                    + ":"
                    + config["password"]
                )
            os.system(
                "transmission-remote "
                + config["host"]
                + auth
                + " --alt-speed"
            )
            context.bot.send_message(
                chat_id=update.effective_message.chat_id,
                text=transcript["Transmission"]["ChangedToTSL"],
            )
            return ConversationHandler.END

        elif choice == transcript["Transmission"]["Normal"]:
            auth = None
            if config["authentication"]:
                auth = (
                    " --auth "
                    + config["username"]
                    + ":"
                    + config["password"]
                )
            os.system(
                "transmission-remote "
                + config["host"]
                + auth
                + " --no-alt-speed"
            )
            context.bot.send_message(
                chat_id=update.effective_message.chat_id,
                text=transcript["Transmission"]["ChangedToNormal"],
            )
            return ConversationHandler.END
