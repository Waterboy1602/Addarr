#!/usr/bin/env python3

import logging
import re
import os

import yaml
from telegram import ReplyKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    Filters,
)

from definitions import CONFIG_PATH, LANG_PATH, CHATID_PATH, ADMIN_PATH
import radarr as radarr
import sonarr as sonarr
import logger

__version__ = "0.3"

config = yaml.safe_load(open(CONFIG_PATH, encoding="utf8"))

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr", logLevel, config.get("logToConsole", False))
logger.debug(f"Addarr v{__version__} starting up...")

SERIE_MOVIE_AUTHENTICATED, READ_CHOICE, GIVE_OPTION, GIVE_PATHS, TSL_NORMAL = range(5)

updater = Updater(config["telegram"]["token"], use_context=True)
dispatcher = updater.dispatcher
lang = config["language"]

transcript = yaml.safe_load(open(LANG_PATH, encoding="utf8"))
transcript = transcript[lang]


def main():
    auth_handler = CommandHandler("entrypointAuth", authentication)
    addMovieserie = ConversationHandler(
        entry_points=[
            CommandHandler(config["entrypointAdd"], startSerieMovie),
            CommandHandler(transcript["Movie"], startSerieMovie),
            CommandHandler(transcript["Serie"], startSerieMovie),
            MessageHandler(
                Filters.regex(
                    re.compile(r"" + config["entrypointAdd"] + "", re.IGNORECASE)
                ),
                startSerieMovie,
            ),
        ],
        states={
            SERIE_MOVIE_AUTHENTICATED: [MessageHandler(Filters.text, choiceSerieMovie)],
            READ_CHOICE: [
                MessageHandler(
                    Filters.regex(f'^({transcript["Movie"]}|{transcript["Serie"]})$'),
                    searchSerieMovie,
                )
            ],
            GIVE_OPTION: [
                MessageHandler(Filters.regex(f'({transcript["Add"]})'), pathSerieMovie),
                MessageHandler(
                    Filters.regex(f'({transcript["Next result"]})'), nextOption
                ),
                MessageHandler(
                    Filters.regex(f'({transcript["New"]})'), startSerieMovie
                ),
            ],
            GIVE_PATHS: [
                MessageHandler(
                    Filters.regex(re.compile(r"^(Path: )(.*)$", re.IGNORECASE)),
                    addSerieMovie,
                ),
            ],
        },
        fallbacks=[
            CommandHandler("stop", stop),
            MessageHandler(Filters.regex("^(Stop|stop)$"), stop),
        ],
    )
    changeTransmissionSpeed = ConversationHandler(
        entry_points=[
            CommandHandler(config["entrypointTransmission"], transmission),
            MessageHandler(
                Filters.regex(
                    re.compile(
                        r"" + config["entrypointTransmission"] + "", re.IGNORECASE
                    )
                ),
                transmission,
            ),
        ],
        states={TSL_NORMAL: [MessageHandler(Filters.text, changeSpeedTransmission)]},
        fallbacks=[
            CommandHandler("stop", stop),
            MessageHandler(Filters.regex("^(Stop|stop)$"), stop),
        ],
    )

    dispatcher.add_handler(auth_handler)
    dispatcher.add_handler(addMovieserie)
    dispatcher.add_handler(changeTransmissionSpeed)

    logger.info(transcript["Start chatting"])
    updater.start_polling()
    updater.idle()


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


def transmission(
    update, context,
):
    if config["transmission"]["enable"]:
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
            if config["transmission"]["authentication"]:
                auth = (
                    " --auth "
                    + config["transmission"]["username"]
                    + ":"
                    + config["transmission"]["password"]
                )
            os.system(
                "transmission-remote "
                + config["transmission"]["host"]
                + auth
                + " --alt-speed"
            )
            context.bot.send_message(
                chat_id=update.effective_message.chat_id,
                text=transcript["Transmission"]["ChangedToTSL"],
            )
            return ConversationHandler.END

        elif choice == transcript["Transmission"]["Normal"]:
            if config["transmission"]["authentication"]:
                auth = (
                    " --auth "
                    + config["transmission"]["username"]
                    + ":"
                    + config["transmission"]["password"]
                )
            os.system(
                "transmission-remote "
                + config["transmission"]["host"]
                + auth
                + " --no-alt-speed"
            )
            context.bot.send_message(
                chat_id=update.effective_message.chat_id,
                text=transcript["Transmission"]["ChangedToNormal"],
            )
            return ConversationHandler.END


def authentication(update, context):
    password = update.message.text
    chatid = update.effective_message.chat_id
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
        return (
            ConversationHandler.END
        )  # This only stops the auth conv, so it goes back to choosing screen


def stop(update, context):
    clearUserData(context)
    context.bot.send_message(
        chat_id=update.effective_message.chat_id, text=transcript["End"]
    )
    return ConversationHandler.END


def startSerieMovie(update, context):
    if checkId(update):
        if update.message.text[1:].lower() in [
            transcript["Serie"].lower(),
            transcript["Movie"].lower(),
        ]:
            logger.debug(
                f"User issued {update.message.text} command, so setting user_data[choice] accordingly"
            )
            context.user_data.update(
                {
                    "choice": transcript["Serie"]
                    if update.message.text[1:].lower() == transcript["Serie"].lower()
                    else transcript["Movie"]
                }
            )
        elif update.message.text.lower() == transcript["New"].lower():
            logger.debug("User issued New command, so clearing user_data")
            clearUserData(context)
        context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=transcript["Title"]
        )
        return SERIE_MOVIE_AUTHENTICATED
    else:
        context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=transcript["Authorize"]
        )
        return SERIE_MOVIE_AUTHENTICATED


def choiceSerieMovie(update, context):
    if not checkId(update):
        if (
            authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END
    else:
        text = update.message.text
        if text[1:].lower() not in [
            transcript["Serie"].lower(),
            transcript["Movie"].lower(),
        ]:
            context.user_data["title"] = text
        if context.user_data.get("choice") in [
            transcript["Serie"],
            transcript["Movie"],
        ]:
            logger.debug(
                f"user_data[choice] is {context.user_data['choice']}, skipping step of selecting movie/series"
            )
            return searchSerieMovie(update, context)
        else:
            reply_keyboard = [[transcript["Movie"], transcript["Serie"]]]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            update.message.reply_text(transcript["What is this?"], reply_markup=markup)
            return READ_CHOICE


def searchSerieMovie(update, context):
    title = context.user_data["title"]
    if context.user_data.get("title"):
        context.user_data.pop("title")
    if not context.user_data.get("choice"):
        choice = update.message.text
        context.user_data["choice"] = choice
    else:
        choice = context.user_data["choice"]
    context.user_data["position"] = 0

    service = getService(context)

    position = context.user_data["position"]
    
    if service.search(title):
        context.user_data["output"] = service.giveTitles(service.search(title))

        reply_keyboard = [
            [transcript[choice.lower()]["Add"], transcript["Next result"]],
            [transcript["New"], transcript["Stop"]],
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=transcript[choice.lower()]["This"],
        )
        context.bot.sendPhoto(
            chat_id=update.effective_message.chat_id,
            photo=context.user_data["output"][position]["poster"],
        )
        text = f"{context.user_data['output'][position]['title']} ({context.user_data['output'][position]['year']})"
        context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=text, reply_markup=markup
        )
        return GIVE_OPTION
    else :
        context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=transcript["No results"],
        )
        clearUserData(context)
        return ConversationHandler.END

def nextOption(update, context):
    position = context.user_data["position"] + 1
    context.user_data["position"] = position

    choice = context.user_data["choice"]

    if position < len(context.user_data["output"]):
        reply_keyboard = [
            [transcript[choice.lower()]["Add"], transcript["Next result"]],
            [transcript["New"], transcript["Stop"]],
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

        context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=transcript[choice.lower()]["This"],
        )
        context.bot.sendPhoto(
            chat_id=update.effective_message.chat_id,
            photo=context.user_data["output"][position]["poster"],
        )
        text = (
            context.user_data["output"][position]["title"]
            + " ("
            + str(context.user_data["output"][position]["year"])
            + ")"
        )
        context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=text, reply_markup=markup
        )
        return GIVE_OPTION
    else:
        context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=transcript["Last result"],
            reply_markup=markup,
        )
        clearUserData(context)
        return ConversationHandler.END

def pathSerieMovie(update, context):
    service = getService(context)
    paths = service.getRootFolders()
    context.user_data.update({"paths": [p["path"] for p in paths]})
    if len(paths) == 1:
        # There is only 1 path, so use it!
        logger.debug("Only found 1 path, so proceeding with that one...")
        context.user_data["path"] = paths[0]["path"]
        return addSerieMovie(update, context)
    formattedPaths = [f"Path: {p['path']}" for p in paths]

    if len(paths) % 2 > 0:
        oddItem = formattedPaths.pop(-1)
    reply_keyboard = [
        [formattedPaths[i], formattedPaths[i + 1]]
        for i in range(0, len(formattedPaths), 2)
    ]
    if len(paths) % 2 > 0:
        reply_keyboard.append([oddItem])
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    context.bot.send_message(
        chat_id=update.effective_message.chat_id,
        text=transcript["Select a path"],
        reply_markup=markup,
    )
    return GIVE_PATHS


def addSerieMovie(update, context):
    position = context.user_data["position"]
    choice = context.user_data["choice"]
    idnumber = context.user_data["output"][position]["id"]

    if not context.user_data.get("path"):
        # Path selection should be in the update message
        if update.message.text.replace("Path: ", "").strip() in context.user_data.get(
            "paths", {}
        ):
            context.user_data["path"] = update.message.text.replace(
                "Path: ", ""
            ).strip()
        else:
            logger.debug(
                f"Message text [{update.message.text.replace('Path: ', '').strip()}] doesn't match any of the paths. Sending paths for selection..."
            )
            return pathSerieMovie(update, context)

    path = context.user_data["path"]
    service = getService(context)

    if not service.inLibrary(idnumber):
        if service.addToLibrary(idnumber, path):
            context.bot.send_message(
                chat_id=update.effective_message.chat_id,
                text=transcript[choice.lower()]["Success"],
            )
            clearUserData(context)
            return ConversationHandler.END
        else:
            context.bot.send_message(
                chat_id=update.effective_message.chat_id,
                text=transcript[choice.lower()]["Failed"],
            )
            clearUserData(context)
            return ConversationHandler.END
    else:
        context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=transcript[choice.lower()]["Exist"],
        )
        clearUserData(context)
        return ConversationHandler.END


def getService(context):
    if context.user_data.get("choice") == transcript["Serie"]:
        return sonarr
    elif context.user_data.get("choice") == transcript["Movie"]:
        return radarr
    else:
        raise ValueError(
            f"Cannot determine service based on unknown or missing choice: {context.user_data.get('choice')}."
        )


def clearUserData(context):
    logger.debug(
        "Removing choice, title, position, paths, and output from context.user_data..."
    )
    for x in [
        x
        for x in ["choice", "title", "position", "output", "paths", "path"]
        if x in context.user_data.keys()
    ]:
        context.user_data.pop(x)


if __name__ == "__main__":
    main()
