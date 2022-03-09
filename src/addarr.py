#!/usr/bin/env python3

import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
import telegram
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          ConversationHandler, Filters, MessageHandler,
                          Updater)

from commons import checkAllowed, checkId, authentication, format_bytes, getAuthChats
import logger
import radarr as radarr
import sonarr as sonarr
import delete as delete
import all as all
from config import checkConfigValues, config, checkConfig
from translations import i18n

__version__ = "0.6"

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr", logLevel, config.get("logToConsole", False))
logger.debug(f"Addarr v{__version__} starting up...")

SERIE_MOVIE_AUTHENTICATED, READ_CHOICE, GIVE_OPTION, GIVE_PATHS, TSL_NORMAL, GIVE_QUALITY_PROFILES, GIVE_SEASONS = range(7)
SERIE_MOVIE_DELETE, READ_DELETE_CHOICE = 0,1

updater = Updater(config["telegram"]["token"], use_context=True)
dispatcher = updater.dispatcher


def startCheck():
    bot = telegram.Bot(token=config["telegram"]["token"])
    missingConfig = checkConfig()
    wrongValues = checkConfigValues()
    check=True
    if missingConfig: #empty list is False
        check = False
        logger.error(i18n.t("addarr.Missing config", missingKeys=f"{missingConfig}"[1:-1]))
        for chat in getAuthChats():
            bot.send_message(chat_id=chat, text=i18n.t("addarr.Missing config", missingKeys=f"{missingConfig}"[1:-1]))
    if wrongValues:
        check=False
        logger.error(i18n.t("addarr.Wrong values", wrongValues=f"{wrongValues}"[1:-1]))
        for chat in getAuthChats():
            bot.send_message(chat_id=chat, text=i18n.t("addarr.Wrong values", wrongValues=f"{wrongValues}"[1:-1]))
    return check


def main():
    auth_handler_command = CommandHandler(config["entrypointAuth"], authentication)
    auth_handler_text = MessageHandler(
                            Filters.regex(
                                re.compile(r"^" + config["entrypointAuth"] + "$", re.IGNORECASE)
                            ),
                            authentication,
                        )
    allSeries_handler_command = CommandHandler(config["entrypointAllSeries"], all.allSeries)
    allSeries_handler_text = MessageHandler(
                            Filters.regex(
                                re.compile(r"^" + config["entrypointAllSeries"] + "$", re.IGNORECASE)
                            ),
                            all.allSeries,
                        )

    allMovies_handler_command = CommandHandler(config["entrypointAllMovies"], all.allMovies)
    allMovies_handler_text = MessageHandler(
        Filters.regex(
            re.compile(r"^" + config["entrypointAllMovies"] + "$", re.IGNORECASE)
        ),
        all.allMovies,
    )

    deleteMovieserie_handler = ConversationHandler(
        entry_points=[
            CommandHandler(config["entrypointDelete"], delete),
            MessageHandler(
                Filters.regex(
                    re.compile(r'^' + config["entrypointDelete"] + '$', re.IGNORECASE)
                ),
                delete.delete,
            ),
        ],
        states={
            SERIE_MOVIE_DELETE: [MessageHandler(Filters.text, choiceSerieMovie)],
            READ_DELETE_CHOICE: [
                MessageHandler(
                    Filters.regex(f'^({i18n.t("addarr.Movie")}|{i18n.t("addarr.Series")})$'),
                    delete.confirmDelete,
                ),
                CallbackQueryHandler(delete.confirmDelete, pattern=f'^({i18n.t("addarr.Movie")}|{i18n.t("addarr.Series")})$')
            ],
            GIVE_OPTION: [
                CallbackQueryHandler(delete.deleteSerieMovie, pattern=f'({i18n.t("addarr.Delete")})'),
                MessageHandler(
                    Filters.regex(f'^({i18n.t("addarr.Delete")})$'),
                    delete.deleteSerieMovie
                ),
                MessageHandler(
                    Filters.regex(f'^({i18n.t("addarr.New")})$'),
                    delete
                ),
                CallbackQueryHandler(delete, pattern=f'({i18n.t("addarr.New")})'),
            ],
        },
        fallbacks=[
            CommandHandler("stop", stop),
            MessageHandler(Filters.regex("^(?i)"+i18n.t("addarr.Stop")+"$"), stop),
            CallbackQueryHandler(stop, pattern=f"^(?i)"+i18n.t("addarr.Stop")+"$"),
        ],
    )

    addMovieserie_handler = ConversationHandler(
        entry_points=[
            CommandHandler(config["entrypointAdd"], startSerieMovie),
            CommandHandler(i18n.t("addarr.Movie"), startSerieMovie),
            CommandHandler(i18n.t("addarr.Series"), startSerieMovie),
            MessageHandler(
                Filters.regex(
                    re.compile(r'^' + config["entrypointAdd"] + '$', re.IGNORECASE)
                ),
                startSerieMovie,
            ),
        ],
        states={
            SERIE_MOVIE_AUTHENTICATED: [MessageHandler(Filters.text, choiceSerieMovie)],
            READ_CHOICE: [
                MessageHandler(
                    Filters.regex(f'^({i18n.t("addarr.Movie")}|{i18n.t("addarr.Series")})$'),
                    searchSerieMovie,
                ),
                CallbackQueryHandler(searchSerieMovie, pattern=f'^({i18n.t("addarr.Movie")}|{i18n.t("addarr.Series")})$'),
                MessageHandler(
                    Filters.regex(f'^({i18n.t("addarr.New")})$'),
                    startSerieMovie
                ),
                CallbackQueryHandler(startSerieMovie, pattern=f'({i18n.t("addarr.New")})'),
            ],
            GIVE_OPTION: [
                CallbackQueryHandler(qualityProfileSerieMovie, pattern=f'({i18n.t("addarr.Select")})'),
                MessageHandler(
                    Filters.regex(f'^({i18n.t("addarr.Select")})$'),
                    qualityProfileSerieMovie
                ),
                CallbackQueryHandler(pathSerieMovie, pattern=f'({i18n.t("addarr.Add")})'),
                MessageHandler(
                    Filters.regex(f'^({i18n.t("addarr.Add")})$'),
                    pathSerieMovie
                ),
                CallbackQueryHandler(nextOption, pattern=f'({i18n.t("addarr.Next result")})'),
                MessageHandler(
                    Filters.regex(f'^({i18n.t("addarr.Next result")})$'),
                    nextOption
                ),
                MessageHandler(
                    Filters.regex(f'^({i18n.t("addarr.New")})$'),
                    startSerieMovie
                ),
                CallbackQueryHandler(startSerieMovie, pattern=f'({i18n.t("addarr.New")})'),
            ],
            GIVE_PATHS: [
                CallbackQueryHandler(qualityProfileSerieMovie, pattern="^(Path: )(.*)$"),
            ],
            GIVE_QUALITY_PROFILES: [
                CallbackQueryHandler(selectSeasons, pattern="^(Quality profile: )(.*)$"),
            ],
            GIVE_SEASONS: [
                CallbackQueryHandler(addSerieMovie, pattern="^(From season: )(.*)$"),
            ],
        },
        fallbacks=[
            CommandHandler("stop", stop),
            MessageHandler(Filters.regex("^(?i)"+i18n.t("addarr.Stop")+"$"), stop),
            CallbackQueryHandler(stop, pattern=f"^(?i)"+i18n.t("addarr.Stop")+"$"),
        ],
    )
    if config["transmission"]["enable"]:
        import transmission as transmission
        changeTransmissionSpeed_handler = ConversationHandler(
            entry_points=[
                CommandHandler(config["entrypointTransmission"], transmission.transmission),
                MessageHandler(
                    Filters.regex(
                        re.compile(
                            r"" + config["entrypointTransmission"] + "", re.IGNORECASE
                        )
                    ),
                    transmission.transmission,
                ),
            ],
            states={
                transmission.TSL_NORMAL: [
                    CallbackQueryHandler(transmission.changeSpeedTransmission),
                ]
            },
            fallbacks=[
                CommandHandler("stop", stop),
                MessageHandler(Filters.regex("^(Stop|stop)$"), stop),
            ],
        )
        dispatcher.add_handler(changeTransmissionSpeed_handler)

    if config["sabnzbd"]["enable"]:
        import sabnzbd as sabnzbd
        changeSabznbdSpeed_handler = ConversationHandler(
            entry_points=[
                CommandHandler(config["entrypointSabnzbd"], sabnzbd.sabnzbd),
                MessageHandler(
                    Filters.regex(
                        re.compile(
                            r"" + config["entrypointSabnzbd"] + "", re.IGNORECASE
                        )
                    ),
                    sabnzbd.sabnzbd,
                ),
            ],
            states={
                sabnzbd.SABNZBD_SPEED_LIMIT_100: [
                    CallbackQueryHandler(sabnzbd.changeSpeedSabnzbd),
                ]
            },
            fallbacks=[
                CommandHandler("stop", stop),
                MessageHandler(Filters.regex("^(Stop|stop)$"), stop),
            ],
        )
        dispatcher.add_handler(changeSabznbdSpeed_handler)

    dispatcher.add_handler(auth_handler_command)
    dispatcher.add_handler(auth_handler_text)
    dispatcher.add_handler(allSeries_handler_command)
    dispatcher.add_handler(allSeries_handler_text)
    dispatcher.add_handler(allMovies_handler_command)
    dispatcher.add_handler(allMovies_handler_text)
    dispatcher.add_handler(addMovieserie_handler)
    dispatcher.add_handler(deleteMovieserie_handler)

    help_handler_command = CommandHandler(config["entrypointHelp"], help)
    dispatcher.add_handler(help_handler_command)

    logger.info(i18n.t("addarr.Start chatting"))
    updater.start_polling()
    updater.idle()


def stop(update, context):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END

    if not checkId(update):
        context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Authorize")
        )
        return SERIE_MOVIE_AUTHENTICATED
        
    clearUserData(context)
    context.bot.send_message(
        chat_id=update.effective_message.chat_id, text=i18n.t("addarr.End")
    )
    return ConversationHandler.END
    

def startSerieMovie(update : Update, context):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END
    
    if not checkId(update):
        context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Authorize")
        )
        return SERIE_MOVIE_AUTHENTICATED

    if update.message is not None:
        reply = update.message.text.lower()
    elif update.callback_query is not None:
        reply = update.callback_query.data.lower()
    else:
        return SERIE_MOVIE_AUTHENTICATED

    if reply[1:] in [
        i18n.t("addarr.Series").lower(),
        i18n.t("addarr.Movie").lower(),
    ]:
        logger.debug(
            f"User issued {reply} command, so setting user_data[choice] accordingly"
        )
        context.user_data.update(
            {
                "choice": i18n.t("addarr.Series")
                if reply[1:] == i18n.t("addarr.Series").lower()
                else i18n.t("addarr.Movie")
            }
        )
    elif reply == i18n.t("addarr.New").lower():
        logger.debug("User issued New command, so clearing user_data")
        clearUserData(context)
    
    msg = context.bot.send_message(
        chat_id=update.effective_message.chat_id, text='\U0001F3F7 '+i18n.t("addarr.Title")
    )
    return SERIE_MOVIE_AUTHENTICATED


def choiceSerieMovie(update, context):
    if not checkId(update):
        if (
            authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END
    elif update.message.text.lower() == "/stop".lower() or update.message.text.lower() == "stop".lower():
        return stop(update, context)
    else:
        if update.message is not None:
            reply = update.message.text
            logger.debug(f"reply is {reply}")
        elif update.callback_query is not None:
            reply = update.callback_query.data
        else:
            return SERIE_MOVIE_AUTHENTICATED

        if reply.lower() not in [
            i18n.t("addarr.Series").lower(),
            i18n.t("addarr.Movie").lower(),
        ]:
            logger.debug(
                f"User entered a title {reply}"
            )
            context.user_data["title"] = reply

        if context.user_data.get("choice") in [
            i18n.t("addarr.Series"),
            i18n.t("addarr.Movie"),
        ]:
            logger.debug(
                f"user_data[choice] is {context.user_data['choice']}, skipping step of selecting movie/series"
            )
            return searchSerieMovie(update, context)
        else:
            keyboard = [
                [
                    InlineKeyboardButton(
                        '\U0001F3AC '+i18n.t("addarr.Movie"),
                        callback_data=i18n.t("addarr.Movie")
                    ),
                    InlineKeyboardButton(
                        '\U0001F4FA '+i18n.t("addarr.Series"),
                        callback_data=i18n.t("addarr.Series")
                    ),
                ],
                [ InlineKeyboardButton(
                        '\U0001F50D '+i18n.t("addarr.New"),
                        callback_data=i18n.t("addarr.New")
                    ),
                ]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            msg = update.message.reply_text(i18n.t("addarr.What is this?"), reply_markup=markup)
            context.user_data["update_msg"] = msg.message_id

        return READ_CHOICE


def searchSerieMovie(update, context):
    title = context.user_data["title"]

    if not context.user_data.get("choice"):
        choice = None
        if update.message is not None:
            choice = update.message.text
        elif update.callback_query is not None:
            choice = update.callback_query.data
        context.user_data["choice"] = choice
    
    choice = context.user_data["choice"]
    context.user_data["position"] = 0

    service = getService(context)

    position = context.user_data["position"]

    keyboard = [
            [
                InlineKeyboardButton(
                    '\U00002795 '+i18n.t("addarr.Add"),
                    callback_data=i18n.t("addarr.Add")
                ),
            ],[
                InlineKeyboardButton(
                    '\U000023ED '+i18n.t("addarr.Next result"),
                    callback_data=i18n.t("addarr.Next result")
                ),
            ],[
                InlineKeyboardButton(
                    '\U0001F5D1 '+i18n.t("addarr.New"),
                    callback_data=i18n.t("addarr.New")
                ),
            ],[
                InlineKeyboardButton(
                    '\U0001F6D1 '+i18n.t("addarr.Stop"),
                    callback_data=i18n.t("addarr.Stop")
                ),
            ],
        ]
    markup = InlineKeyboardMarkup(keyboard)
    
    searchResult = service.search(title)
    if not searchResult:
        context.bot.send_message( 
            chat_id=update.effective_message.chat_id, 
            text=i18n.t("addarr.searchresults", count=0),
        )
        clearUserData(context)
        return ConversationHandler.END

    context.user_data["output"] = service.giveTitles(searchResult)
    message=i18n.t("addarr.searchresults", count=len(searchResult))
    message += f"\n\n*{context.user_data['output'][position]['title']} ({context.user_data['output'][position]['year']})*"
    
    if "update_msg" in context.user_data:
        context.bot.edit_message_text(
            message_id=context.user_data["update_msg"],
            chat_id=update.effective_message.chat_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        msg = context.bot.send_message(chat_id=update.effective_message.chat_id, text=message,parse_mode=ParseMode.MARKDOWN,)
        context.user_data["update_msg"] = msg.message_id
    
    img = context.bot.sendPhoto(
        chat_id=update.effective_message.chat_id,
        photo=context.user_data["output"][position]["poster"],
    )
    context.user_data["photo_update_msg"] = img.message_id
    
    if choice == i18n.t("addarr.Movie"):
        message=i18n.t("addarr.messages.This", subjectWithArticle=i18n.t("addarr.MovieWithArticle").lower())
    else:
        message=i18n.t("addarr.messages.This", subjectWithArticle=i18n.t("addarr.SeriesWithArticle").lower())
    msg = context.bot.send_message(
        chat_id=update.effective_message.chat_id, text=message, reply_markup=markup
    )
    context.user_data["title_update_msg"] = context.user_data["update_msg"]
    context.user_data["update_msg"] = msg.message_id
    
    return GIVE_OPTION


def nextOption(update, context):
    position = context.user_data["position"] + 1
    context.user_data["position"] = position
    searchResult = context.user_data["output"]
    choice = context.user_data["choice"]    
    message=i18n.t("addarr.searchresults", count=len(searchResult))
    message += f"\n\n*{context.user_data['output'][position]['title']} ({context.user_data['output'][position]['year']})*"
    context.bot.edit_message_text(
        message_id=context.user_data["title_update_msg"],
        chat_id=update.effective_message.chat_id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
    )
    
    if position < len(context.user_data["output"]):
        keyboard = [
                [
                    InlineKeyboardButton(
                        '\U00002795 '+i18n.t("addarr.Add"),
                        callback_data=i18n.t("addarr.Add")
                    ),
                ],[
                    InlineKeyboardButton(
                        '\U000023ED '+i18n.t("addarr.Next result"),
                        callback_data=i18n.t("addarr.Next result")
                    ),
                ],[
                    InlineKeyboardButton(
                        '\U0001F5D1 '+i18n.t("addarr.New"),
                        callback_data=i18n.t("addarr.New")
                    ),
                ],[
                    InlineKeyboardButton(
                        '\U0001F6D1 '+i18n.t("addarr.Stop"),
                        callback_data=i18n.t("addarr.Stop")
                    ),
                ],
            ]
        markup = InlineKeyboardMarkup(keyboard)

        context.bot.delete_message(
            message_id=context.user_data["photo_update_msg"],
            chat_id=update.effective_message.chat_id,
        )
        
        img = context.bot.sendPhoto(
            chat_id=update.effective_message.chat_id,
            photo=context.user_data["output"][position]["poster"],
        )
        context.user_data["photo_update_msg"] = img.message_id
        
        context.bot.delete_message(
            message_id=context.user_data["update_msg"],
            chat_id=update.effective_message.chat_id,
        )
        if choice == i18n.t("addarr.Movie"):
            message=i18n.t("addarr.messages.This", subjectWithArticle=i18n.t("addarr.MovieWithArticle").lower())
        else:
            message=i18n.t("addarr.messages.This", subjectWithArticle=i18n.t("addarr.SeriesWithArticle").lower())
        msg = context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=message, reply_markup=markup
        )
        context.user_data["update_msg"] = msg.message_id
        return GIVE_OPTION
    else:
        context.bot.edit_message_text(
            message_id=context.user_data["update_msg"],
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.Last result")
        )
        clearUserData(context)
        return ConversationHandler.END


def pathSerieMovie(update, context):
    service = getService(context)
    paths = service.getRootFolders()
    excluded_root_folders = service.config.get("excludedRootFolders", [])
    paths = [p for p in paths if p["path"] not in excluded_root_folders]
    logger.debug(f"Excluded root folders: {excluded_root_folders}")
    context.user_data.update({"paths": [p["path"] for p in paths]})
    if len(paths) == 1:
        # There is only 1 path, so use it!
        logger.debug("Only found 1 path, so proceeding with that one...")
        context.user_data["path"] = paths[0]["path"]
        return qualityProfileSerieMovie(update, context)
        
    keyboard = []
    for p in paths:
        free = format_bytes(p['freeSpace'])
        keyboard += [[
            InlineKeyboardButton(
                f"Path: {p['path']}, Free: {free}",
                callback_data=f"Path: {p['path']}"
            ),
        ]]
    markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        message_id=context.user_data["update_msg"],
        chat_id=update.effective_message.chat_id,
        text=i18n.t("addarr.Select a path"),
        reply_markup=markup,
    )
    return GIVE_PATHS


def qualityProfileSerieMovie(update, context):
    if not context.user_data.get("path"):
        # Path selection should be in the update message
        path = None
        if update.callback_query is not None:
            try_path = update.callback_query.data.replace("Path: ", "").strip()
            if try_path in context.user_data.get("paths", {}):
                context.user_data["path"] = try_path
                path = try_path
        if path is None:
            logger.debug(
                f"Callback query [{update.callback_query.data.replace('Path: ', '').strip()}] doesn't match any of the paths. Sending paths for selection..."
            )
            return pathSerieMovie(update, context)

    service = getService(context)

    excluded_quality_profiles = service.config.get("excludedQualityProfiles", [])
    qualityProfiles = service.getQualityProfiles()
    qualityProfiles = [q for q in qualityProfiles if q["name"] not in excluded_quality_profiles]
    
    context.user_data.update({"qualityProfiles": [q['id'] for q in qualityProfiles]})
    if len(qualityProfiles) == 1:
        # There is only 1 path, so use it!
        logger.debug("Only found 1 profile, so proceeding with that one...")
        context.user_data["qualityProfile"] = qualityProfiles[0]['id']
        return selectSeasons(update, context)

    keyboard = []
    for q in qualityProfiles:
        keyboard += [[
            InlineKeyboardButton(
                f"Quality: {q['name']}",
                callback_data=f"Quality profile: {q['id']}"
            ),
        ]]
    markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        message_id=context.user_data["update_msg"],
        chat_id=update.effective_message.chat_id,
        text=i18n.t("addarr.Select a quality"),
        reply_markup=markup,
    )
    return GIVE_QUALITY_PROFILES


def selectSeasons(update, context):
    if not context.user_data.get("qualityProfile"):
        # Quality selection should be in the update message
        qualityProfile = None
        if update.callback_query is not None:
            try_qualityProfile = update.callback_query.data.replace("Quality profile: ", "").strip()
            if int(try_qualityProfile) in context.user_data.get("qualityProfiles", {}):
                context.user_data["qualityProfile"] = try_qualityProfile
                qualityProfile = int(try_qualityProfile)
        if qualityProfile is None:
            logger.debug(
                f"Callback query [{update.callback_query.data.replace('Quality profile: ', '').strip()}] doesn't match any of the quality profiles. Sending quality profiles for selection..."
            )
            return qualityProfileSerieMovie(update, context)

    service = getService(context)
    if service == radarr:
        return addSerieMovie(update, context)
    
    position = context.user_data["position"]
    idnumber = context.user_data["output"][position]["id"]
    seasons = service.getSeasons(idnumber)
    seasonNumbers = [s["seasonNumber"] for s in seasons]
    context.user_data["seasons"] = seasonNumbers
    
    keyboard = [[InlineKeyboardButton(i18n.t("addarr.Future seasons"),callback_data="From season: Future")]]    
    for s in seasonNumbers:
        keyboard += [[
            InlineKeyboardButton(
                f"{i18n.t('addarr.From season')} {s}",
                callback_data=f"From season: {s}"
            ),
        ]]
    markup = InlineKeyboardMarkup(keyboard)

    context.bot.edit_message_text(
        message_id=context.user_data["update_msg"],
        chat_id=update.effective_message.chat_id,
        text=i18n.t("addarr.Select from which season"),
        reply_markup=markup,
    )
    return GIVE_SEASONS


def addSerieMovie(update, context):
    position = context.user_data["position"]
    choice = context.user_data["choice"]
    idnumber = context.user_data["output"][position]["id"]
    path = context.user_data["path"]
    service = getService(context)
    
    if choice == i18n.t("addarr.Series"):
        if not context.user_data.get("selectedSeasons"):
            # Season selection should be in the update message
            selectedSeasons = None
            if update.callback_query is not None:
                try_fromSeason = update.callback_query.data.replace("From season: ", "").strip()
                if try_fromSeason == "Future": 
                    selectedSeasons = []
                else:
                    selectedSeasons = [int(s) for s in context.user_data["seasons"] if int(s) >= int(try_fromSeason)]
                context.user_data["selectedSeasons"] = selectedSeasons
            if selectedSeasons is None:
                logger.debug(
                    f"Callback query [{update.callback_query.data.replace('From season: ', '').strip()}] doesn't match any of the season options. Sending seasons for selection..."
                )
                return selectSeasons(update, context)
        seasons = context.user_data["seasons"]
        selectedSeasons = context.user_data["selectedSeasons"]
        seasonsSelected = []
        for s in seasons:
            monitored = False
            if s in selectedSeasons:
                monitored = True
                
            seasonsSelected.append(
                {
                    "seasonNumber": s,
                    "monitored": monitored,
                }
            )
        logger.debug(f"Seasons {seasonsSelected} have been selected.")
    
    qualityProfile = context.user_data["qualityProfile"]
    #Currently not working, on development
    #[service.createTag(dt) for dt in service.config.get("defaultTags", []) if dt not in service.getTags()]
    tags = [int(t["id"]) for t in service.getTags() if t["label"] in service.config.get("defaultTags", [])]
    logger.debug(f"Tags {tags} have been selected.")
    
    if not service.inLibrary(idnumber):
        if choice == i18n.t("addarr.Movie"):
            added = service.addToLibrary(idnumber, path, qualityProfile, tags)
        else:
            added = service.addToLibrary(idnumber, path, qualityProfile, tags, seasonsSelected)
        
        if added:
            if choice == i18n.t("addarr.Movie"):
                message=i18n.t("addarr.messages.AddSuccess", subjectWithArticle=i18n.t("addarr.MovieWithArticle"))
            else:
                message=i18n.t("addarr.messages.AddSuccess", subjectWithArticle=i18n.t("addarr.SeriesWithArticle"))
            context.bot.edit_message_text(
                message_id=context.user_data["update_msg"],
                chat_id=update.effective_message.chat_id,
                text=message,
            )
            clearUserData(context)
            return ConversationHandler.END
        else:
            if choice == i18n.t("addarr.Movie"):
                message=i18n.t("addarr.messages.AddFailed", subjectWithArticle=i18n.t("addarr.MovieWithArticle").lower())
            else:
                message=i18n.t("addarr.messages.AddFailed", subjectWithArticle=i18n.t("addarr.SeriesWithArticle").lower())
            context.bot.edit_message_text(
                message_id=context.user_data["update_msg"],
                chat_id=update.effective_message.chat_id,
                text=message,
            )
            clearUserData(context)
            return ConversationHandler.END
    else:
        if choice == i18n.t("addarr.Movie"):
            message=i18n.t("addarr.messages.Exist", subjectWithArticle=i18n.t("addarr.MovieWithArticle"))
        else:
            message=i18n.t("addarr.messages.Exist", subjectWithArticle=i18n.t("addarr.SeriesWithArticle"))
        context.bot.edit_message_text(
            message_id=context.user_data["update_msg"],
            chat_id=update.effective_message.chat_id,
            text=message,
        )
        clearUserData(context)
        return ConversationHandler.END


def getService(context):
    if context.user_data.get("choice") == i18n.t("addarr.Series"):
        return sonarr
    elif context.user_data.get("choice") == i18n.t("addarr.Movie"):
        return radarr
    else:
        raise ValueError(
            f"Cannot determine service based on unknown or missing choice: {context.user_data.get('choice')}."
        )


def help(update, context):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END
    
    context.bot.send_message(
        chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Help",
            help=config["entrypointHelp"],
            authenticate=config["entrypointAuth"],
            add=config["entrypointAdd"],
            delete=config["entrypointDelete"],
            serie='serie',
            movie='movie',
            allSeries=config["entrypointAllSeries"],
            allMovies=config["entrypointAllMovies"],
            transmission=config["entrypointTransmission"],
            sabnzbd=config["entrypointSabnzbd"],
        )
    )
    return ConversationHandler.END


def clearUserData(context):
    logger.debug(
        "Removing choice, title, position, paths, and output from context.user_data..."
    )
    for x in [
        x
        for x in ["choice", "title", "position", "output", "paths", "path", "qualityProfiles", "qualityProfile", "update_msg", "title_update_msg", "photo_update_msg", "selectedSeasons", "seasons"]
        if x in context.user_data.keys()
    ]:
        context.user_data.pop(x)


if __name__ == "__main__":
    if startCheck():
        main()
    else:
        import sys
        sys.exit(0)
