#!/usr/bin/env python3

import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import telegram
from telegram.constants import ParseMode
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          ConversationHandler, filters, MessageHandler,
                          Application)
from telegram.warnings import PTBUserWarning

from commons import checkAllowed, checkId, authentication, format_bytes, getAuthChats
import logger
import radarr as radarr
import sonarr as sonarr
import delete as delete
import all as all
from config import checkConfigValues, config, checkConfig
from translations import i18n
from warnings import filterwarnings

import asyncio

__version__ = "0.8"

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr", logLevel, config.get("logToConsole", False))
logger.debug(f"Addarr v{__version__} starting up...")

MEDIA_AUTHENTICATED, READ_CHOICE, GIVE_OPTION, GIVE_INSTANCE, GIVE_PATHS, GIVE_QUALITY_PROFILES, SELECT_SEASONS = range (7)

application = Application.builder().token(config["telegram"]["token"]).build()

async def startCheck():
    bot = telegram.Bot(token=config["telegram"]["token"])
    missingConfig = checkConfig()
    wrongValues = checkConfigValues()
    check=True
    if missingConfig: #empty list is False
        check = False
        logger.error(i18n.t("addarr.Missing config", missingKeys=f"{missingConfig}"[1:-1]))
        for chat in getAuthChats():
            await bot.send_message(chat_id=chat, text=i18n.t("addarr.Missing config", missingKeys=f"{missingConfig}"[1:-1]))
    if wrongValues:
        check=False
        logger.error(i18n.t("addarr.Wrong values", wrongValues=f"{wrongValues}"[1:-1]))
        for chat in getAuthChats():
            await bot.send_message(chat_id=chat, text=i18n.t("addarr.Wrong values", wrongValues=f"{wrongValues}"[1:-1]))
    return check


def main():
    filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

    auth_handler_command = CommandHandler(config["entrypointAuth"], authentication)
    auth_handler_text = MessageHandler(
                            filters.Regex(
                                re.compile(r"^" + config["entrypointAuth"] + "$", re.IGNORECASE)
                            ),
                            authentication,
                        )
    
    allSeries_handler_command = CommandHandler(config["entrypointAllSeries"], all.allSeries)
    allSeries_handler_text = MessageHandler(
                            filters.Regex(
                                re.compile(r"^" + config["entrypointAllSeries"] + "$", re.IGNORECASE)
                            ),
                            all.allSeries,
                        )

    allMovies_handler_command = CommandHandler(config["entrypointAllMovies"], all.allMovies)
    allMovies_handler_text = MessageHandler(
        filters.Regex(
            re.compile(r"^" + config["entrypointAllMovies"] + "$", re.IGNORECASE)
        ),
        all.allMovies,
    )

    deleteMedia_handler = ConversationHandler(
        entry_points=[
            CommandHandler(config["entrypointDelete"], delete.startDelete),
            MessageHandler(
                filters.Regex(
                    re.compile(r'^' + config["entrypointDelete"] + '$', re.IGNORECASE)
                ),
                delete.startDelete,
            ),
        ],
        states={
            delete.MEDIA_DELETE_AUTHENTICATED: [MessageHandler(filters.TEXT, delete.storeDeleteTitle)],

            delete.MEDIA_DELETE_TYPE:[
                MessageHandler(
                    filters.Regex(f'^({i18n.t("addarr.Movie")}|{i18n.t("addarr.Series")})$'),
                    delete.storeDeleteMediaType
                ),
                CallbackQueryHandler(delete.storeDeleteMediaType, pattern=f'^({i18n.t("addarr.Movie")}|{i18n.t("addarr.Series")})$'),
                MessageHandler(
                    filters.Regex(f'^({i18n.t("addarr.New")})$'),
                    delete.startDelete
                ),
                CallbackQueryHandler(delete.startDelete, pattern=f'({i18n.t("addarr.New")})'),
            ],

            delete.GIVE_INSTANCE: [CallbackQueryHandler(delete.storeMediaInstance, pattern=r"^instance=(.+)")],
            
            delete.DELETE_CONFIRM:[
                CallbackQueryHandler(delete.deleteMedia, pattern=f'({i18n.t("addarr.Delete")})'),
                MessageHandler(
                    filters.Regex(f'^({i18n.t("addarr.Delete")})$'),
                    delete.deleteMedia
                ),
                MessageHandler(
                    filters.Regex(f'^({i18n.t("addarr.New")})$'),
                    delete.deleteMedia
                ),
                CallbackQueryHandler(delete.deleteMedia, pattern=f'({i18n.t("addarr.New")})'),  
            ],
        },
        fallbacks=[
            CommandHandler("stop", stop),
            MessageHandler(filters.Regex("(?i)^"+i18n.t("addarr.Stop")+"$"), stop),
            CallbackQueryHandler(stop, pattern=f"(?i)^"+i18n.t("addarr.Stop")+"$"),
        ],
    )

    addMedia_handler = ConversationHandler(
        entry_points=[
            CommandHandler(config["entrypointAdd"], startNewMedia),
            CommandHandler(i18n.t("addarr.Movie"), startNewMedia),
            CommandHandler(i18n.t("addarr.Series"), startNewMedia),
            MessageHandler(
                filters.Regex(
                    re.compile(
                        rf'^{i18n.t("addarr.Find")} ((?:{i18n.t("addarr.Movie")}|{i18n.t("addarr.Series")})) (.+)$',
                        re.IGNORECASE
                    )
                ),
                storeTitle,
            ),
        ],
        states={
            MEDIA_AUTHENTICATED: [
                MessageHandler(filters.TEXT, storeTitle),
                CallbackQueryHandler(storeTitle, pattern=rf'^{i18n.t("addarr.Movie")}$|^{i18n.t("addarr.Series")}$'),
            ],
            READ_CHOICE: [
                MessageHandler(
                    filters.Regex(f'^({i18n.t("addarr.Movie")}|{i18n.t("addarr.Series")})$'),
                    storeMediaType,
                ),
                CallbackQueryHandler(storeMediaType, pattern=f'^({i18n.t("addarr.Movie")}|{i18n.t("addarr.Series")})$'),
                MessageHandler(
                    filters.Regex(f'^({i18n.t("addarr.New")})$'),
                    startNewMedia
                ),
                CallbackQueryHandler(startNewMedia, pattern=f'({i18n.t("addarr.New")})'),
            ],
            GIVE_INSTANCE: [CallbackQueryHandler(storeInstance, pattern=r"^instance=(.+)")],
            GIVE_OPTION: [
                CallbackQueryHandler(storeSelection, pattern=f'({i18n.t("addarr.Add")})'),
                MessageHandler(
                    filters.Regex(f'^({i18n.t("addarr.Add")})$'),
                    storeSelection
                ),
                CallbackQueryHandler(nextOption, pattern=f'({i18n.t("addarr.Next result")})'),
                MessageHandler(
                    filters.Regex(f'^({i18n.t("addarr.Next result")})$'),
                    nextOption
                ),
                MessageHandler(
                    filters.Regex(f'^({i18n.t("addarr.New")})$'),
                    startNewMedia
                ),
                CallbackQueryHandler(startNewMedia, pattern=f'({i18n.t("addarr.New")})'),
            ],
            GIVE_PATHS: [
                CallbackQueryHandler(storePath, pattern="^(Path: )(.*)$"),
            ],
            GIVE_QUALITY_PROFILES: [
                CallbackQueryHandler(storeQualityProfile, pattern="^(Quality profile: )(.*)$"),
            ],
            SELECT_SEASONS: [
                CallbackQueryHandler(storeSeasons, pattern="^(Season: )(.*)$"),
            ],
        },
        fallbacks=[
            CommandHandler("stop", stop),
            MessageHandler(filters.Regex("(?i)^"+i18n.t("addarr.Stop")+"$"), stop),
            CallbackQueryHandler(stop, pattern=f"(?i)^"+i18n.t("addarr.Stop")+"$"),
        ],
    )
    
    if config["transmission"]["enable"]:
        import transmission as transmission
        changeTransmissionSpeed_handler = ConversationHandler(
            entry_points=[
                CommandHandler(config["entrypointTransmission"], transmission.transmission),
                MessageHandler(
                    filters.Regex(
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
                MessageHandler(filters.Regex("^(Stop|stop)$"), stop),
            ],
        )
        application.add_handler(changeTransmissionSpeed_handler)

    if config["sabnzbd"]["enable"]:
        import sabnzbd as sabnzbd
        changeSabznbdSpeed_handler = ConversationHandler(
            entry_points=[
                CommandHandler(config["entrypointSabnzbd"], sabnzbd.sabnzbd),
                MessageHandler(
                    filters.Regex(
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
                MessageHandler(filters.Regex("^(Stop|stop)$"), stop),
            ],
        )
        application.add_handler(changeSabznbdSpeed_handler)
    
    if config["qbittorrent"]["enable"]:
        import qbittorrent as qbittorrent
        changeqBittorrentSpeed_handler = ConversationHandler(
            entry_points=[
                CommandHandler(config["entrypointqBittorrent"], qbittorrent.qbittorrent),
                MessageHandler(
                    filters.Regex(
                        re.compile(
                            r"" + config["entrypointqBittorrent"] + "", re.IGNORECASE
                        )
                    ),
                    qbittorrent.qbittorrent,
                ),
            ],
            states={
                qbittorrent.QBITTORRENT_SPEED_NORMAL: [
                    CallbackQueryHandler(qbittorrent.changeSpeedqBittorrent),
                ]
            },
            fallbacks=[
                CommandHandler("stop", stop),
                MessageHandler(filters.Regex("^(Stop|stop)$"), stop),
            ],
        )
        application.add_handler(changeqBittorrentSpeed_handler)

    application.add_handler(auth_handler_command)
    application.add_handler(auth_handler_text)
    application.add_handler(allSeries_handler_command)
    application.add_handler(allSeries_handler_text)
    application.add_handler(allMovies_handler_command)
    application.add_handler(allMovies_handler_text)
    application.add_handler(addMedia_handler)
    application.add_handler(deleteMedia_handler)

    help_handler_command = CommandHandler(config["entrypointHelp"], help)
    application.add_handler(help_handler_command)

    logger.info(i18n.t("addarr.Start chatting"))
    application.run_polling()

async def stop(update, context):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END

    if not checkId(update):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Authorize")
        )
        return MEDIA_AUTHENTICATED
        
    if not checkAllowed(update,"admin") and config.get("adminNotifyId") is not None:
        adminNotifyId = config.get("adminNotifyId")
        await context.bot.send_message(
            chat_id=adminNotifyId, text=i18n.t("addarr.Notifications.Stop", first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
        )
    clearUserData(context)
    await context.bot.send_message(
        chat_id=update.effective_message.chat_id, text=i18n.t("addarr.End")
    )
    return ConversationHandler.END


async def startNewMedia(update : Update, context):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END
    
    if not checkId(update):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Authorize")
        )
        return MEDIA_AUTHENTICATED

    if update.message is not None:
        reply = update.message.text.lower()
    elif update.callback_query is not None:
        reply = update.callback_query.data.lower()
    else:
        return MEDIA_AUTHENTICATED
    
    if i18n.t("addarr.Movie").lower() in reply:
        logger.debug(
            f"User issued {reply} command, so setting user_data[choice] accordingly"
        )
        context.user_data["choice"] = i18n.t("addarr.Movie")
    elif i18n.t("addarr.Series").lower() in reply:
        logger.debug(
            f"User issued {reply} command, so setting user_data[choice] accordingly"
        )
        context.user_data["choice"] = i18n.t("addarr.Series")
    elif reply.lower() == i18n.t("addarr.New").lower():
        logger.debug("User issued New command, so clearing user_data")
        clearUserData(context)


    await context.bot.send_message(
        chat_id=update.effective_message.chat_id, text='\U0001F3F7 '+i18n.t("addarr.Title")
    )

    if not checkAllowed(update,"admin") and config.get("adminNotifyId") is not None:
        adminNotifyId = config.get("adminNotifyId")
        await context.bot.send_message(
            chat_id=adminNotifyId, text=i18n.t("addarr.Notifications.Start", first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
        )

    return MEDIA_AUTHENTICATED


async def storeMediaType(update, context):
    if not checkId(update):
        if (
            await authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END
    else:
        choice = None
        if update.message is not None:
            choice = update.message.text
        elif update.callback_query is not None:
            choice = update.callback_query.data
        context.user_data["choice"] = choice
        logger.info(f'choice: {choice}')

    await promptInstanceSelection(update, context)
    return GIVE_INSTANCE
        
async def storeTitle(update : Update, context):
    if not checkId(update):
        if (
            await authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END
    elif update.message.text.lower() == "/stop".lower() or update.message.text.lower() == "stop".lower():
        return await stop(update, context)
    else:
        if update.message is not None:
            reply = update.message.text.lower()
        elif update.callback_query is not None:
            reply = update.callback_query.data
        else:
            return MEDIA_AUTHENTICATED

        #check if its a single line command
        singleLineCommand = re.match(
            rf'^{i18n.t("addarr.Find")} ({i18n.t("addarr.Movie")}|{i18n.t("addarr.Series")}) (.+)$',
            reply,
            re.IGNORECASE,
        )

        if singleLineCommand:
            logger.debug(
                f"User issued single line command {reply}"
            )
            # there will be a title and choice in it. extract it.
            adv_cmd = re.match(
                rf'^{i18n.t("addarr.Find")} ((?:{i18n.t("addarr.Movie")}|{i18n.t("addarr.Series")})) (.+)$',
                reply,
                re.IGNORECASE,
            )
            if adv_cmd:
                context.user_data["choice"] = singleLineCommand.group(1)
                context.user_data["title"] = singleLineCommand.group(2)
                logger.debug(
                    f"User is looking for a {singleLineCommand.group(2)}, named {singleLineCommand.group(1)}"
                )
            else:
                logger.warning(f"There was an error parseing single line command {reply}")
        else:
            if context.user_data.get("title") is None:
                logger.info(f"Storing {reply} as title")
                context.user_data["title"] = reply
                if context.user_data.get("choice") is None:
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
                    msg = await update.message.reply_text(i18n.t("addarr.What is this?"), reply_markup=markup)
                    context.user_data["update_msg"] = msg.message_id
                    return READ_CHOICE

        
        await promptInstanceSelection(update, context)
        return GIVE_INSTANCE

async def promptInstanceSelection(update : Update, context):
    service_name = 'radarr' if context.user_data["choice"].lower() == i18n.t("addarr.Movie").lower() else 'sonarr'
    instances = config[service_name] 
    if len(instances) == 1:
           # There is only 1 instance, so use it!
           logger.debug(f"Only found 1 instance of {service_name}, so proceeding with that one...")
           context.user_data["instance"] = instances[0]["label"]
           return await storeInstance(update, context) # skip to next step
    keyboard = []
    for instance in instances:
        label = instance['label']
        keyboard += [[
            InlineKeyboardButton(
            label,
            callback_data=f"instance={label}"
            ),
        ]]
    markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        msg = await update.message.reply_text(
            text=i18n.t("addarr.Select an instance"),
            reply_markup=markup
        )
    else:
        msg = await update.effective_chat.send_message(
            text=i18n.t("addarr.Select an instance"),
            reply_markup=markup
        )
    context.user_data["update_msg"] = msg.message_id

async def storeInstance(update : Update, context):
    # store selected instance and give out search results
    if update.message is not None:
        reply = update.message.text.lower()
        logger.debug(f"reply is {reply}")
    elif update.callback_query is not None:
        reply = update.callback_query.data
    else:
        return MEDIA_AUTHENTICATED
    
    if reply.startswith("instance="):
        label = reply.replace("instance=", "", 1)
    else:
        label = reply
    
    context.user_data["instance"] = label
    
    instance = context.user_data["instance"]
    title = context.user_data["title"]
    choice = context.user_data["choice"]
    position = context.user_data["position"] = 0
    service = getService(context)
    service.setInstance(instance)

    searchResult = service.search(title)

    if not searchResult:
        await context.bot.send_message( 
            chat_id=update.effective_message.chat_id, 
            text=i18n.t("addarr.searchresults", count=0),
        )
        clearUserData(context)
        return ConversationHandler.END

    context.user_data["output"] = service.giveTitles(searchResult)
    message=i18n.t("addarr.searchresults", count=len(searchResult))
    message += f"\n\n*{context.user_data['output'][position]['title']} ({context.user_data['output'][position]['year']})*"
    
    if "update_msg" in context.user_data:
        await context.bot.edit_message_text(
            message_id=context.user_data["update_msg"],
            chat_id=update.effective_message.chat_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        msg = await context.bot.send_message(chat_id=update.effective_message.chat_id, text=message,parse_mode=ParseMode.MARKDOWN,)
        context.user_data["update_msg"] = msg.message_id
    
    try:
        img = await context.bot.sendPhoto(
            chat_id=update.effective_message.chat_id,
            photo=context.user_data["output"][position]["poster"],
        )
    except:
        context.user_data["photo_update_msg"] = None
    else:
        context.user_data["photo_update_msg"] = img.message_id
    
    if len(searchResult) == 1:
        keyboard = [
            [
                InlineKeyboardButton(
                    '\U00002795 '+i18n.t("addarr.Add"),
                    callback_data=i18n.t("addarr.Add")
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
    else: 
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

    if choice.lower() == i18n.t("addarr.Movie").lower():
        message=i18n.t("addarr.messages.This", subjectWithArticle=i18n.t("addarr.MovieWithArticle").lower())
    else:
        message=i18n.t("addarr.messages.This", subjectWithArticle=i18n.t("addarr.SeriesWithArticle").lower())
    msg = await context.bot.send_message(
        chat_id=update.effective_message.chat_id, text=message, reply_markup=markup
    )
    context.user_data["title_update_msg"] = context.user_data["update_msg"]
    context.user_data["update_msg"] = msg.message_id

    return GIVE_OPTION


async def nextOption(update, context):
    position = context.user_data["position"] + 1
    context.user_data["position"] = position
    searchResult = context.user_data["output"]
    choice = context.user_data["choice"]    

    message=i18n.t("addarr.searchresults", count=len(searchResult))
    message += f"\n\n*{context.user_data['output'][position]['title']} ({context.user_data['output'][position]['year']})*"
    await context.bot.edit_message_text(
        message_id=context.user_data["title_update_msg"],
        chat_id=update.effective_message.chat_id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
    )
    
    if position < len(context.user_data["output"]) - 1:
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
    else:
        keyboard = [
            [
                InlineKeyboardButton(
                    '\U00002795 '+i18n.t("addarr.Add"),
                    callback_data=i18n.t("addarr.Add")
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

    if context.user_data["photo_update_msg"]:
        await context.bot.delete_message(
            message_id=context.user_data["photo_update_msg"],
            chat_id=update.effective_message.chat_id,
        )
    
    try:
        img = await context.bot.sendPhoto(
            chat_id=update.effective_message.chat_id,
            photo=context.user_data["output"][position]["poster"],
        )
    except:
        context.user_data["photo_update_msg"] = None
    else:
        context.user_data["photo_update_msg"] = img.message_id
    
    await context.bot.delete_message(
        message_id=context.user_data["update_msg"],
        chat_id=update.effective_message.chat_id,
    )
    if choice.lower() == i18n.t("addarr.Movie").lower():
        message=i18n.t("addarr.messages.This", subjectWithArticle=i18n.t("addarr.MovieWithArticle").lower())
    else:
        message=i18n.t("addarr.messages.This", subjectWithArticle=i18n.t("addarr.SeriesWithArticle").lower())
    msg = await context.bot.send_message(
        chat_id=update.effective_message.chat_id, text=message, reply_markup=markup
    )
    context.user_data["update_msg"] = msg.message_id
    return GIVE_OPTION


async def storeSelection(update : Update, context):
    # store the selected movie and prompt which root folder to use

    # variables in context.user_data will keep track of what the user selected based on position and stuff
    # so we dont really have to "store" anything here this time

    service = getService(context)
    service.setInstance(context.user_data["instance"])
    
    paths = service.getRootFolders()
    excluded_root_folders = service.config.get("excludedRootFolders", [])
    paths = [p for p in paths if p["path"] not in excluded_root_folders]
    logger.debug(f"Excluded root folders: {excluded_root_folders}")

    context.user_data.update({"paths": [p["path"] for p in paths]})
    if len(paths) == 1:
        # There is only 1 path, so use it!
        logger.debug("Only found 1 path, so proceeding with that one...")
        context.user_data["path"] = paths[0]["path"]
        return await storePath(update, context) # go back to previous step
    
    keyboard = []
    for p in paths:
        pathtxt = p['path']
        if service.config.get("narrowRootFolderNames"):
            pathlst = p['path'].split("/")
            pathtxt = pathlst[len(pathlst)-1]
        free = format_bytes(p['freeSpace'])
        keyboard += [[
            InlineKeyboardButton(
            f"Path: {pathtxt}, Free: {free}",
            callback_data=f"Path: {p['path']}"
            ),
        ]]
    markup = InlineKeyboardMarkup(keyboard)

    await context.bot.edit_message_text(
        message_id=context.user_data["update_msg"],
        chat_id=update.effective_message.chat_id,
        text=i18n.t("addarr.Select a path"),
        reply_markup=markup,
    )
    
    return GIVE_PATHS


async def storePath(update : Update, context):
    # store selected root folder and prompt to select quality profiles
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
            return await storeSelection(update, context)  # go back to previous step
    
    service = getService(context)
    service.setInstance(context.user_data["instance"])

    excluded_quality_profiles = service.config.get("excludedQualityProfiles", [])
    qualityProfiles = service.getQualityProfiles()
    qualityProfiles = [q for q in qualityProfiles if q["name"] not in excluded_quality_profiles]
    logger.debug(f"Excluded quality profiles: {excluded_quality_profiles}")

    context.user_data.update({"qualityProfiles": [q['id'] for q in qualityProfiles]})
    if len(qualityProfiles) == 1:
        # There is only 1 quality profile, so use it!
        logger.debug("Only found 1 profile, so proceeding with that one...")
        context.user_data["qualityProfile"] = qualityProfiles[0]['id']
        return await qualityProfiles(update, context)

    keyboard = []
    for q in qualityProfiles:
        keyboard += [[
            InlineKeyboardButton(
                f"Quality: {q['name']}",
                callback_data=f"Quality profile: {q['id']}"
            ),
        ]]
    markup = InlineKeyboardMarkup(keyboard)

    await context.bot.edit_message_text(
        message_id=context.user_data["update_msg"],
        chat_id=update.effective_message.chat_id,
        text=i18n.t("addarr.Select a quality"),
        reply_markup=markup,
    )

    return GIVE_QUALITY_PROFILES


async def storeQualityProfile(update : Update, context):
    # store quality profile selection and save the movie. 
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
            return storePath(update, context) # go back to previous step
        
    service = getService(context)
    service.setInstance(context.user_data["instance"])

    if service == radarr:
        return await addMedia(update, context)
        
    position = context.user_data["position"]
    idnumber = context.user_data["output"][position]["id"]
    seasons = service.getSeasons(idnumber)
    seasonNumbers = [s["seasonNumber"] for s in seasons]
    context.user_data["seasons"] = seasonNumbers
    selectedSeasons = []

    keyboard = [[InlineKeyboardButton('\U0001F5D3 ' + i18n.t("addarr.Selected and future seasons"),callback_data="Season: Future and selected")]]
    for s in seasonNumbers:
        keyboard += [[
            InlineKeyboardButton(
                "\U00002705 " + f"{i18n.t('addarr.Season')} {s}",
                callback_data=f"Season: {s}"
            ),
        ]]
        selectedSeasons.append(int(s))

    keyboard += [[InlineKeyboardButton(i18n.t("addarr.Deselect all seasons"),callback_data=f"Season: None")]]

    markup = InlineKeyboardMarkup(keyboard)

    context.user_data["selectedSeasons"] = selectedSeasons

    await context.bot.edit_message_text(
        message_id=context.user_data["update_msg"],
        chat_id=update.effective_message.chat_id,
        text=i18n.t("addarr.Select from which season"),
        reply_markup=markup,
    )

    return SELECT_SEASONS


async def storeSeasons(update, context):
    choice = context.user_data["choice"]
    seasons = context.user_data["seasons"]
    selectedSeasons = []
    if "selectedSeasons" in context.user_data:
        selectedSeasons = context.user_data["selectedSeasons"]
 
    if choice.lower() == i18n.t("addarr.Series").lower():
        if update.callback_query is not None:
            insertSeason = update.callback_query.data.replace("Season: ", "").strip()
            if insertSeason == "Future and selected":
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
                
                context.user_data["selectedSeasons"] = selectedSeasons
                return await addMedia(update, context)
              
            else:
                if insertSeason == "All":
                    for s in seasons:
                        if s not in selectedSeasons:
                            selectedSeasons.append(s)
                elif insertSeason == "None":
                    for s in seasons:
                        if s in selectedSeasons:
                            selectedSeasons.remove(s)
                elif int(insertSeason) not in selectedSeasons:
                    selectedSeasons.append(int(insertSeason))
                else:
                    selectedSeasons.remove(int(insertSeason))
                    
                context.user_data["selectedSeasons"] = selectedSeasons
                keyboard = [[InlineKeyboardButton('\U0001F5D3 ' + i18n.t("addarr.Selected and future seasons"),callback_data="Season: Future and selected")]]
                for s in seasons:
                    if s in selectedSeasons: 
                        season = "\U00002705 " + f"{i18n.t('addarr.Season')} {s}" 
                    else:
                        season = "\U00002B1C " + f"{i18n.t('addarr.Season')} {s}"

                    keyboard.append([
                        InlineKeyboardButton(
                            season,
                            callback_data=f"Season: {s}"
                        )
                    ])
                
                if len(selectedSeasons) == len(seasons):
                    keyboard += [[InlineKeyboardButton(i18n.t("addarr.Deselect all seasons"),callback_data=f"Season: None")]]
                else:
                    keyboard += [[InlineKeyboardButton(i18n.t("addarr.Select all seasons"),callback_data=f"Season: All")]]

                markup = InlineKeyboardMarkup(keyboard)

                await context.bot.edit_message_text(
                    message_id=context.user_data["update_msg"],
                    chat_id=update.effective_message.chat_id,
                    text=i18n.t("addarr.Select from which season"),
                    reply_markup=markup,
                )
                return SELECT_SEASONS
            
        if selectedSeasons is None:
            logger.debug(
                f"Callback query [{update.callback_query.data.replace('From season: ', '').strip()}] doesn't match any of the season options. Sending seasons for selection..."
            )
            return await storeSeasons(update, context) 
        
async def addMedia(update, context):
    position = context.user_data["position"]
    choice = context.user_data["choice"]
    idnumber = context.user_data["output"][position]["id"]
    path = context.user_data["path"]
    service = getService(context)
    service.setInstance(context.user_data["instance"])

    if choice.lower() == i18n.t("addarr.Series").lower():
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

    # Process the tags that will be added
    tags = []
    service_Config = service.getInstance()
    
    if service_Config.get("addRequesterIdTag"):
        userTag = str(update.effective_message.chat.id)
        if service.tagExists(userTag) != -1:
            tags = [userTag]
            logger.debug(f'The tag {userTag} already exists. Using existing tag for user')
        else:
            logger.debug(f'The tag {userTag} does not exists. Creating new tag for user')
            newTag = service.createTag(userTag)
            if newTag >=0: 
                tags = [newTag]
            else:
                instace_name = service.getInstance()
                logger.debug(f'Create user tag FAILED in {instace_name}: {userTag}')
    else:
        logger.debug("tagging not included")
    if not tags:
        logger.debug(f'Adding default tags')
        default_tags = service_Config.get("defaultTags", [])
        for tag in default_tags:
            if str(tag) not in [str(t["label"]) for t in service.getTags()]:
                newTag = service.createTag(str(tag))
                tags.append(newTag)
    
    if not service.inLibrary(idnumber):
        if choice.lower() == i18n.t("addarr.Movie").lower():
            added = service.addToLibrary(idnumber, path, qualityProfile, tags)
        else:
            added = service.addToLibrary(idnumber, path, qualityProfile, tags, seasonsSelected)
        
        if added:
            if choice.lower() == i18n.t("addarr.Movie").lower():
                message=i18n.t("addarr.messages.AddSuccess", subjectWithArticle=i18n.t("addarr.MovieWithArticle"))
            else:
                message=i18n.t("addarr.messages.AddSuccess", subjectWithArticle=i18n.t("addarr.SeriesWithArticle"))
            await context.bot.edit_message_text(
                message_id=context.user_data["update_msg"],
                chat_id=update.effective_message.chat_id,
                text=message,
            )
            if not checkAllowed(update,"admin") and config.get("adminNotifyId") is not None:
                adminNotifyId = config.get("adminNotifyId")
                if choice.lower() == i18n.t("addarr.Movie").lower():
                    message2=i18n.t("addarr.Notifications.AddSuccess", subjectWithArticle=i18n.t("addarr.MovieWithArticle"),title=context.user_data['output'][position]['title'],first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
                else:
                    message2=i18n.t("addarr.Notifications.AddSuccess", subjectWithArticle=i18n.t("addarr.SeriesWithArticle"),title=context.user_data['output'][position]['title'],first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
                await context.bot.send_message(
                    chat_id=adminNotifyId, text=message2
                )
            clearUserData(context)
            return ConversationHandler.END
        else:
            if choice.lower() == i18n.t("addarr.Movie").lower():
                message=i18n.t("addarr.messages.AddFailed", subjectWithArticle=i18n.t("addarr.MovieWithArticle").lower())
            else:
                message=i18n.t("addarr.messages.AddFailed", subjectWithArticle=i18n.t("addarr.SeriesWithArticle").lower())
            await context.bot.edit_message_text(
                message_id=context.user_data["update_msg"],
                chat_id=update.effective_message.chat_id,
                text=message,
            )
            if not checkAllowed(update,"admin") and config.get("adminNotifyId") is not None:
                adminNotifyId = config.get("adminNotifyId")
                if choice.lower() == i18n.t("addarr.Movie").lower():
                    message2=i18n.t("addarr.Notifications.AddFailed", subjectWithArticle=i18n.t("addarr.MovieWithArticle"),title=context.user_data['output'][position]['title'],first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
                else:
                    message2=i18n.t("addarr.Notifications.AddFailed", subjectWithArticle=i18n.t("addarr.SeriesWithArticle"),title=context.user_data['output'][position]['title'],first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
                await context.bot.send_message(
                    chat_id=adminNotifyId, text=message2
                )
            clearUserData(context)
            return ConversationHandler.END
    else:
        if choice.lower() == i18n.t("addarr.Movie").lower():
            message=i18n.t("addarr.messages.Exist", subjectWithArticle=i18n.t("addarr.MovieWithArticle"))
        else:
            message=i18n.t("addarr.messages.Exist", subjectWithArticle=i18n.t("addarr.SeriesWithArticle"))
        await context.bot.edit_message_text(
            message_id=context.user_data["update_msg"],
            chat_id=update.effective_message.chat_id,
            text=message,
        )
            
        if not checkAllowed(update,"admin") and config.get("adminNotifyId") is not None:
            adminNotifyId = config.get("adminNotifyId")
            if choice.lower() == i18n.t("addarr.Movie").lower():
                message2=i18n.t("addarr.Notifications.Exist", subjectWithArticle=i18n.t("addarr.MovieWithArticle"),title=context.user_data['output'][position]['title'],first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
            else:
                message2=i18n.t("addarr.Notifications.Exist", subjectWithArticle=i18n.t("addarr.SeriesWithArticle"),title=context.user_data['output'][position]['title'],first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
            await context.bot.send_message(
                chat_id=adminNotifyId, text=message2
            )
        clearUserData(context)
        return ConversationHandler.END

def getService(context):
    if context.user_data.get("choice").lower() == i18n.t("addarr.Series").lower():
        return sonarr
    elif context.user_data.get("choice").lower() == i18n.t("addarr.Movie").lower():
        return radarr
    else:
        raise ValueError(
            f"Cannot determine service based on unknown or missing choice: {context.user_data.get('choice')}"
        )
    

async def help(update, context):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END
    
    await context.bot.send_message(
        chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Help",
            help=config["entrypointHelp"],
            authenticate=config["entrypointAuth"],
            add=config["entrypointAdd"],
            delete=config["entrypointDelete"],
            movie=i18n.t("addarr.Movie").lower(),
            serie=i18n.t("addarr.Series").lower(),
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
    loop = asyncio.get_event_loop()
    if loop.run_until_complete(startCheck()):
        main()
        loop.close()
    else:
        import sys
        sys.exit(0)
