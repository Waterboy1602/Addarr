import yaml
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

from commons import checkId
from definitions import CONFIG_PATH

config = yaml.safe_load(open(CONFIG_PATH, encoding="utf8"))
config = config["radarr"]

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
                    ]
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

# Check if user is an admin
def checkAdmin(update):
    admin = False
    user = update.message.from_user
    with open(ADMIN_PATH, "r") as file:
        for line in file:
            if line.strip("\n") == str(user["username"]) or line.strip("\n") == str(
                user["id"]
            ):
                admin = True
        file.close()
        if admin:
            return True
        else:
            return False