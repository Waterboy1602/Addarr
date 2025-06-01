#!/usr/bin/env python3

import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import telegram
from telegram.constants import ParseMode
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          ConversationHandler, filters, MessageHandler,
                          ContextTypes, Application)
from telegram.warnings import PTBUserWarning

from commons import (checkAllowed, checkId, authentication,
                    format_bytes, getAuthChats, getService, clearUserData, 
                    checkNotificationSubscribed, generateProfileName)
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

MEDIA_AUTHENTICATED, GIVE_MEDIA_TYPE, GIVE_OPTION, GIVE_INSTANCE, GIVE_PATHS, GIVE_QUALITY_PROFILES, SELECT_SEASONS = range (7)


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([('start', 'Starts the bot')])

    commands = [
        (config["entrypointAuth"].lower(), i18n.t("addarr.CommandDescriptions.Authenticate")),
        (config["entrypointAdd"].lower(), i18n.t("addarr.CommandDescriptions.Add")),
        (config["entrypointHelp"].lower(), i18n.t("addarr.CommandDescriptions.Help")),
        (i18n.t("addarr.General.Movie").lower(), i18n.t("addarr.CommandDescriptions.Movie")),
        (i18n.t("addarr.General.Series").lower(), i18n.t("addarr.CommandDescriptions.Series")),
        (config["entrypointDelete"].lower(), i18n.t("addarr.CommandDescriptions.Delete")),
        (config["entrypointAllMovies"].lower(), i18n.t("addarr.CommandDescriptions.AllMovies")),
        (config["entrypointAllSeries"].lower(), i18n.t("addarr.CommandDescriptions.AllSeries")),
        (config["entrypointTransmission"].lower(), i18n.t("addarr.CommandDescriptions.Transmission")),
        (config["entrypointSabnzbd"].lower(), i18n.t("addarr.CommandDescriptions.Sabnzbd")),
        (config["entrypointqBittorrent"].lower(), i18n.t("addarr.CommandDescriptions.qBittorrent")),
        (config["entrypointNotify"].lower(), i18n.t("addarr.CommandDescriptions.Notify")),
    ]

    await application.bot.set_my_commands(commands)

application = Application.builder().token(config["telegram"]["token"]).post_init(post_init).build()

async def startCheck():
    bot = telegram.Bot(token=config["telegram"]["token"])
    missingConfig = checkConfig()
    wrongValues = checkConfigValues()
    check=True
    if missingConfig: #empty list is False
        check = False
        logger.error(i18n.t("addarr.Messages.MissingConfig", missingKeys=f"{missingConfig}"[1:-1]))
        for chat in getAuthChats():
            await bot.send_message(chat_id=chat, text=i18n.t("addarr.Messages.MissingConfig", missingKeys=f"{missingConfig}"[1:-1]))
    if wrongValues:
        check=False
        logger.error(i18n.t("addarr.Messages.ConfigError", wrongValues=f"{wrongValues}"[1:-1]))
        for chat in getAuthChats():
            await bot.send_message(chat_id=chat, text=i18n.t("addarr.Messages.ConfigError", wrongValues=f"{wrongValues}"[1:-1]))
    return check


def main():
    filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

    auth_handler_command = CommandHandler(config["entrypointAuth"], authentication)
    auth_handler_text = MessageHandler(
          filters.Regex(
               re.compile(r"^/?"+ re.escape(config["entrypointAuth"]) + r"(?:\s.*)?$", re.IGNORECASE)
          ),
          authentication,
    )
    
    notification_handler_command = CommandHandler(config["entrypointNotify"], addNotificationChannel)
    notification_handler_text = MessageHandler(
          filters.Regex(
               re.compile(r"^/?"+ re.escape(config["entrypointNotify"]) + r"(?:\s.*)?$", re.IGNORECASE)
          ),
          addNotificationChannel,
    )

    listAllMediaHandler = ConversationHandler(
        entry_points=[
                CommandHandler(config["entrypointAllSeries"], all.startAllSeries),
                
                CommandHandler(config["entrypointAllMovies"], all.startAllMovies),

                MessageHandler(
                    filters.Regex(
                        re.compile(r"^" + config["entrypointAllSeries"] + "$", re.IGNORECASE)
                    ),
                    all.startAllSeries,
                ),

                MessageHandler(
                    filters.Regex(
                        re.compile(r"^" + config["entrypointAllMovies"] + "$", re.IGNORECASE)
                    ),
                    all.startAllMovies,
                ),
        ],
        states={
            all.LS_GIVE_MOVIE_INSTANCE: [
                CallbackQueryHandler(all.sendAll, pattern=r"^instance=(.+)")
            ],
            all.LS_GIVE_SERIE_INSTANCE: [
                CallbackQueryHandler(all.sendAll, pattern=r"^instance=(.+)")
            ],
        },
        fallbacks=[
            CommandHandler("stop", stop),
            MessageHandler(filters.Regex("(?i)^"+i18n.t("addarr.General.Stop")+"$"), stop),
            CallbackQueryHandler(stop, pattern=f"(?i)^"+i18n.t("addarr.General.Stop")+"$"), 
        ]
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
                    filters.Regex(f'^({i18n.t("addarr.General.Movie")}|{i18n.t("addarr.General.Series")})$'),
                    delete.storeDeleteMediaType
                ),
                CallbackQueryHandler(delete.storeDeleteMediaType, pattern=f'^({i18n.t("addarr.General.Movie")}|{i18n.t("addarr.General.Series")})$'),
                MessageHandler(
                    filters.Regex(f'^({i18n.t("addarr.General.New")})$'),
                    delete.startDelete
                ),
                CallbackQueryHandler(delete.startDelete, pattern=f'({i18n.t("addarr.General.New")})'),
            ],

            delete.GIVE_INSTANCE: [CallbackQueryHandler(delete.storeMediaInstance, pattern=r"^instance=(.+)")],
            
            delete.DELETE_CONFIRM:[
                CallbackQueryHandler(stop, pattern=f'({i18n.t("addarr.Actions.StopDelete")})'),
                MessageHandler(
                    filters.Regex(f'^({i18n.t("addarr.Actions.StopDelete")})$'),
                    stop
                ),
                CallbackQueryHandler(delete.deleteMedia, pattern=f'({i18n.t("addarr.Actions.Delete")})'),
                MessageHandler(
                    filters.Regex(f'^({i18n.t("addarr.Actions.Delete")})$'),
                    delete.deleteMedia
                ),
                MessageHandler(
                    filters.Regex(f'^({i18n.t("addarr.General.New")})$'),
                    delete.startDelete
                ),
                CallbackQueryHandler(delete.startDelete, pattern=f'({i18n.t("addarr.General.New")})'),  
            ],
        },
        fallbacks=[
            CommandHandler("stop", stop),
            MessageHandler(filters.Regex("(?i)^"+i18n.t("addarr.General.Stop")+"$"), stop),
            CallbackQueryHandler(stop, pattern=f"(?i)^"+i18n.t("addarr.General.Stop")+"$"),
        ],
    )

    addMedia_handler = ConversationHandler(
        entry_points=[
            CommandHandler(config["entrypointAdd"], startNewMedia),
            CommandHandler(i18n.t('addarr.General.Series'), startNewMedia),
            CommandHandler(i18n.t('addarr.General.Movie'), startNewMedia),
            MessageHandler(
                filters.Regex(
                    re.compile(rf"^{config['entrypointAdd']}$", re.IGNORECASE)
                ),
                startNewMedia,
            ),
            MessageHandler(
                filters.Regex(
                    re.compile(rf"^{i18n.t('addarr.General.Movie')}$", re.IGNORECASE)
                ),
                startNewMedia,
            ),
             MessageHandler(
                filters.Regex(
                    re.compile(rf"^{i18n.t('addarr.General.Series')}$", re.IGNORECASE)
                ),
                startNewMedia,
            ),
            MessageHandler(
                filters.Regex(
                    re.compile(
                        rf"^((?:{i18n.t('addarr.General.Movie')}|{i18n.t('addarr.General.Series')})) (.+)$",
                        re.IGNORECASE
                    )
                ),
                storeTitle,
            ),
        ],
        states={
            MEDIA_AUTHENTICATED: [
                MessageHandler(filters.TEXT, storeTitle),
                CallbackQueryHandler(storeTitle, pattern=rf'^{i18n.t("addarr.General.Movie")}$|^{i18n.t("addarr.General.Series")}$'),
            ],
            GIVE_MEDIA_TYPE: [
                MessageHandler(
                    filters.Regex(f'(?i)^({i18n.t("addarr.General.Movie")}|{i18n.t("addarr.General.Series")})$'),
                    storeMediaType,
                ),
                CallbackQueryHandler(storeMediaType, pattern=f'^({i18n.t("addarr.General.Movie")}|{i18n.t("addarr.General.Series")})$'),
                MessageHandler(
                    filters.Regex(f'(?i)^({i18n.t("addarr.General.New")})$'),
                    startNewMedia
                ),
                CallbackQueryHandler(startNewMedia, pattern=f'(?i)^({i18n.t("addarr.General.New")})'),
            ],
            GIVE_INSTANCE: [
                CallbackQueryHandler(storeInstance, pattern="^instance=(.+)$"),
            ],
            GIVE_OPTION: [
                CallbackQueryHandler(storeSelection, pattern=f'(?i)^({i18n.t("addarr.Actions.Add")})$'),
                CallbackQueryHandler(prevOption, pattern=f'(?i)^({i18n.t("addarr.General.PreviousResult")})$'),
                CallbackQueryHandler(nextOption, pattern=f'(?i)^({i18n.t("addarr.General.NextResult")})$'),
                CallbackQueryHandler(startNewMedia, pattern=f'(?i)^({i18n.t("addarr.General.New")})$'),
                MessageHandler(
                    filters.Regex(f'(?i)^({i18n.t("addarr.Actions.Add")})$'),
                    storeSelection
                ),
                MessageHandler(
                    filters.Regex(f'(?i)^({i18n.t("addarr.General.PreviousResult")})$'),
                    prevOption
                ),
                MessageHandler(
                    filters.Regex(f'(?i)^({i18n.t("addarr.General.NextResult")})$'),
                    nextOption
                ),
                MessageHandler(
                    filters.Regex(f'(?i)^({i18n.t("addarr.General.New")})'),
                    startNewMedia
                ),
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
            MessageHandler(filters.Regex("(?i)^"+i18n.t("addarr.General.Stop")+"$"), stop),
            CallbackQueryHandler(stop, pattern=f"(?i)^"+i18n.t("addarr.General.Stop")+"$"),
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
                            rf'^{config["entrypointTransmission"]}$', re.IGNORECASE
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
                MessageHandler(filters.Regex("(?i)^"+i18n.t("addarr.General.Stop")+"$"), stop),
                CallbackQueryHandler(stop, pattern=f"(?i)^"+i18n.t("addarr.General.Stop")+"$"),
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
                            rf'^{config["entrypointSabnzbd"]}$', re.IGNORECASE
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
                MessageHandler(filters.Regex("(?i)^"+i18n.t("addarr.General.Stop")+"$"), stop),
                CallbackQueryHandler(stop, pattern=f"(?i)^"+i18n.t("addarr.General.Stop")+"$"),
            ],
        )
        application.add_handler(changeSabznbdSpeed_handler)
    
    if config["qbittorrent"]["enable"]:
        import qbittorrent as qbittorrent
        
        changeqBittorrentSpeed_handler = ConversationHandler(
            entry_points=[
                CommandHandler(config["entrypointqBittorrent"], qbittorrent.qbittorrent),
                MessageHandler(
                    filters.Regex(rf'(?i)^{config["entrypointqBittorrent"]}$'),
                    qbittorrent.qbittorrent,
                ),

            ],
            states={
                qbittorrent.QBT_AUTHENTICATE: [
                    CallbackQueryHandler(qbittorrent.qbittorrent, pattern=rf"(?i)^{config['entrypointqBittorrent']}$"),
                ],
                qbittorrent.QBT_GIVE_SPEED_TYPES: [
                    CallbackQueryHandler(qbittorrent.setClientSpeed, pattern=r"^speedtype=(.+)$"),
                ],
            },
            fallbacks=[
                CommandHandler("stop", stop),
                MessageHandler(filters.Regex("(?i)^"+i18n.t("addarr.General.Stop")+"$"), stop),
                CallbackQueryHandler(stop, pattern=f"(?i)^"+i18n.t("addarr.General.Stop")+"$"),
            ],
        )

        application.add_handler(changeqBittorrentSpeed_handler)

    application.add_handler(auth_handler_command)
    application.add_handler(auth_handler_text)

    application.add_handler(notification_handler_command)
    application.add_handler(notification_handler_text)

    application.add_handler(listAllMediaHandler)
    application.add_handler(addMedia_handler)
    application.add_handler(deleteMedia_handler)

    help_handler_command = CommandHandler(config["entrypointHelp"], help)
    application.add_handler(help_handler_command)

    logger.info(i18n.t("addarr.Messages.StartChatting"))
    application.run_polling()


async def stop(update : Update, context: ContextTypes.DEFAULT_TYPE):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END

    if not checkId(update):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Authorization.Authorize")
        )
        return MEDIA_AUTHENTICATED
        
    if not checkAllowed(update,"admin") and config.get("adminNotifyId") is not None:
        adminNotifyId = config.get("adminNotifyId")
        await context.bot.send_message(
            chat_id=adminNotifyId, text=i18n.t("addarr.AdminNotifications.Stop", first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
        )
    clearUserData(context)
    await context.bot.send_message(
        chat_id=update.effective_message.chat_id, text=i18n.t("addarr.General.End")
    )
    return ConversationHandler.END


async def startNewMedia(update : Update, context: ContextTypes.DEFAULT_TYPE):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END
    
    if not checkId(update):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Authorization.Authorize")
        )
        return MEDIA_AUTHENTICATED

    if update.message is not None:
        reply = update.message.text.lower()
    elif update.callback_query is not None:
        reply = update.callback_query.data.lower()
    else:
        return MEDIA_AUTHENTICATED

    
    if i18n.t("addarr.General.Movie").lower() in reply.lower():
        logger.debug(
            f"User issued {reply} command, so processing for Movie."
        )
        # Check if the reply contains only "Movie" (ignoring case and a leading "/")
        cleaned_reply = reply.lstrip("/").strip().lower()
        if cleaned_reply == i18n.t("addarr.General.Movie").lower():
            context.user_data["choice"] = i18n.t("addarr.General.Movie")
        else:
            # Separate "Movie" from the rest of the words
            remaining_text = cleaned_reply.replace(i18n.t("addarr.General.Movie").lower(), "").strip()
            context.user_data["choice"] = i18n.t("addarr.General.Movie")
            context.user_data["title"] = remaining_text
            logger.debug(f"Command: Movie, Title: {remaining_text}")
            
            # Prompt user to select the instance
            service_name = 'radarr' if context.user_data["choice"].lower() == i18n.t("addarr.General.Movie").lower() else 'sonarr'
            instances = config[service_name]["instances"] 
    
            if len(instances) == 1:
                # There is only 1 instance, so use it!
                logger.debug(f"Only found 1 instance of {service_name}, so proceeding with that one...")
                context.user_data["instance"] = instances[0]["label"]
                await storeInstance(update, context) # skip to next step
                return GIVE_OPTION
    
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

            if not config.get("update_msg"):
                msg = await context.bot.send_message(
                    chat_id=update.effective_message.chat_id, 
                    text=i18n.t("addarr.General.SelectAnInstance"),
                    reply_markup=markup,
                )
                context.user_data["update_msg"] = msg.message_id
            else: 
                await context.bot.edit_message_text(
                    message_id=context.user_data["update_msg"],
                    chat_id=update.effective_message.chat_id,
                    text=i18n.t("addarr.General.SelectAnInstance"),
                    reply_markup=markup,
                )
            
            return GIVE_INSTANCE


    elif i18n.t("addarr.General.Series").lower() in reply.lower():
        logger.debug(
            f"User issued {reply} command, so processing for Series."
        )
        # Check if the reply contains only "Series" (ignoring case and a leading "/")
        cleaned_reply = reply.lstrip("/").strip().lower()
        if cleaned_reply == i18n.t("addarr.General.Series").lower():
            context.user_data["choice"] = i18n.t("addarr.General.Series")
        else:
            # Separate "Series" from the rest of the words
            remaining_text = cleaned_reply.replace(i18n.t("addarr.General.Series").lower(), "").strip()
            context.user_data["choice"] = i18n.t("addarr.General.Series")
            context.user_data["title"] = remaining_text
            logger.debug(f"Command: Series, Title: {remaining_text}")
            
            # Prompt user to select the instance
            service_name = 'radarr' if context.user_data["choice"].lower() == i18n.t("addarr.General.Movie").lower() else 'sonarr'
            instances = config[service_name]["instances"] 

            if len(instances) == 1:
                # There is only 1 instance, so use it!
                logger.debug(f"Only found 1 instance of {service_name}, so proceeding with that one...")
                context.user_data["instance"] = instances[0]["label"]
                await storeInstance(update, context) # skip to next step
                return GIVE_OPTION

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

            if not config.get("update_msg"):
                msg = await context.bot.send_message(
                    chat_id=update.effective_message.chat_id, 
                    text=i18n.t("addarr.General.SelectAnInstance"),
                    reply_markup=markup,
                )
                context.user_data["update_msg"] = msg.message_id
            else: 
                await context.bot.edit_message_text(
                    message_id=context.user_data["update_msg"],
                    chat_id=update.effective_message.chat_id,
                    text=i18n.t("addarr.General.SelectAnInstance"),
                    reply_markup=markup,
                )

            return GIVE_INSTANCE

    elif reply.lower() == i18n.t("addarr.General.New").lower():
        logger.debug("User issued New command, so clearing user_data")
        clearUserData(context)



    if i18n.t("addarr.General.Movie").lower() in reply:
        logger.debug(
            f"User issued {reply} command, so setting user_data[choice] accordingly"
        )
        context.user_data["choice"] = i18n.t("addarr.General.Movie")

    elif i18n.t("addarr.General.Series").lower() in reply:
        logger.debug(
            f"User issued {reply} command, so setting user_data[choice] accordingly"
        )
        context.user_data["choice"] = i18n.t("addarr.General.Series")

    elif reply.lower() == i18n.t("addarr.General.New").lower():
        logger.debug("User issued New command, so clearing user_data")
        clearUserData(context)


    await context.bot.send_message(
        chat_id=update.effective_message.chat_id, text='\U0001F3F7 '+i18n.t("addarr.General.Title")
    )

    if not checkAllowed(update,"admin") and config.get("adminNotifyId") is not None:
        logger.debug('Sending admin notification')
        adminNotifyId = config.get("adminNotifyId")
        await context.bot.send_message(
            chat_id=adminNotifyId, 
            text=i18n.t("addarr.AdminNotifications.Start", first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
        )

    return MEDIA_AUTHENTICATED


async def storeMediaType(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not checkId(update):
        if (await authentication(update, context) == "added"):  # To also stop the beginning command
            return ConversationHandler.END
    else:
        choice = None
        if update.message is not None:
            choice = update.message.text.lower()
        elif update.callback_query is not None:
            choice = update.callback_query.data.lower()
        context.user_data["choice"] = choice
        logger.info(f'choice: {choice}')

        # Prompt user to select instance
        service_name = 'radarr' if context.user_data["choice"].lower() == i18n.t("addarr.General.Movie").lower() else 'sonarr'
        instances = config[service_name]["instances"] 

        if len(instances) == 1:
            # There is only 1 instance, so use it!
            logger.debug(f"Only found 1 instance of {service_name}, so proceeding with that one...")
            context.user_data["instance"] = instances[0]["label"]
            await storeInstance(update, context) # skip to next step
            return GIVE_OPTION

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

        await context.bot.edit_message_text(
            message_id=context.user_data["update_msg"],
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.General.SelectAnInstance"),
            reply_markup=markup,
        )
        
        return GIVE_INSTANCE


async def storeTitle(update : Update, context: ContextTypes.DEFAULT_TYPE):
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
            reply = update.callback_query.data.lower()
        else:
            return MEDIA_AUTHENTICATED

        #check if its a single line command
        singleLineCommand = re.match(
            rf'^({i18n.t("addarr.General.Movie")}|{i18n.t("addarr.General.Series")}) (.+)$',
            reply,
            re.IGNORECASE,
        )

        if singleLineCommand:
            logger.debug(
                f"User issued single line command {reply}"
            )
            # there will be a title and choice in it. extract it.
            adv_cmd = re.match(
                rf'^((?:{i18n.t("addarr.General.Movie")}|{i18n.t("addarr.General.Series")})) (.+)$',
                reply,
                re.IGNORECASE,
            )
            if adv_cmd:
                context.user_data["choice"] = singleLineCommand.group(1).lower()
                context.user_data["title"] = singleLineCommand.group(2)
                logger.debug(
                    f"User is looking for a {singleLineCommand.group(1)} named '{singleLineCommand.group(2)}'"
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
                                '\U0001F3AC '+i18n.t("addarr.General.Movie"),
                                callback_data=i18n.t("addarr.General.Movie")
                            ),
                            InlineKeyboardButton(
                                '\U0001F4FA '+i18n.t("addarr.General.Series"),
                                callback_data=i18n.t("addarr.General.Series")
                            ),
                        ],
                        [ InlineKeyboardButton(
                                '\U0001F50D '+i18n.t("addarr.General.New"),
                                callback_data=i18n.t("addarr.General.New")
                            ),
                        ]
                    ]
                    markup = InlineKeyboardMarkup(keyboard)
                    msg = await update.message.reply_text(i18n.t("addarr.General.WhatIsThis"), reply_markup=markup)
                    context.user_data["update_msg"] = msg.message_id
                    return GIVE_MEDIA_TYPE

        # Prompt user to select the instance
        service_name = 'radarr' if context.user_data["choice"].lower() == i18n.t("addarr.General.Movie").lower() else 'sonarr'
        instances = config[service_name]["instances"] 

        if len(instances) == 1:
            # There is only 1 instance, so use it!
            logger.debug(f"Only found 1 instance of {service_name}, so proceeding with that one...")
            context.user_data["instance"] = instances[0]["label"]
            await storeInstance(update, context) # skip to next step
            return GIVE_OPTION

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

        if not config.get("update_msg"):
            msg = await context.bot.send_message(
                chat_id=update.effective_message.chat_id, 
                text=i18n.t("addarr.General.SelectAnInstance"),
                reply_markup=markup,
            )
            context.user_data["update_msg"] = msg.message_id
        else: 
            await context.bot.edit_message_text(
                message_id=context.user_data["update_msg"],
                chat_id=update.effective_message.chat_id,
                text=i18n.t("addarr.General.SelectAnInstance"),
                reply_markup=markup,
            )
        
        return GIVE_INSTANCE


async def storeInstance(update : Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
       
    # store selected instance and give out search results
    if update.message is not None:
        reply = update.message.text.lower()
        logger.debug(f"reply is {reply}")
    elif update.callback_query is not None:
        reply = update.callback_query.data.lower()
    else:
        return MEDIA_AUTHENTICATED
    
    if not context.user_data.get("instance"):
        if reply.startswith("instance="):
            label = reply.replace("instance=", "", 1)
        else:
            label = reply
        context.user_data["instance"] = label
    else:
        logger.debug("Instance set from previous function")


    instance = context.user_data["instance"]
    title = context.user_data["title"]
    choice = context.user_data["choice"]
    position = context.user_data["position"] = 0

    service = getService(context)
    service.setInstance(instance)
    searchResult = service.search(title)

    if not searchResult:
        logger.warning("No results found.")
        await context.bot.send_message( 
            chat_id=update.effective_message.chat_id, 
            text=i18n.t("addarr.SearchResults", count=0),
        )
        clearUserData(context)
        return ConversationHandler.END

    context.user_data["output"] = service.giveTitles(searchResult)
    message=i18n.t("addarr.SearchResults", count=len(searchResult))
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
    
    
    keyboard = [
        [
            InlineKeyboardButton(
                '\U00002795 ' + i18n.t("addarr.Actions.Add"),
                callback_data=i18n.t("addarr.Actions.Add")
            ),
        ],
    ]

    # Row for Prev and Next buttons
    prev_next_row = []
    if position > 0:
        prev_next_row.append(
            InlineKeyboardButton(
                '\U000023EE ' + i18n.t("addarr.General.PreviousResult"),
                callback_data=i18n.t("addarr.General.PreviousResult")
            )
        )
    if position < len(context.user_data["output"]) - 1:
        prev_next_row.append(
            InlineKeyboardButton(
                '\U000023ED ' + i18n.t("addarr.General.NextResult"),
                callback_data=i18n.t("addarr.General.NextResult")
            )
        )

    # Add Prev/Next row only if it has buttons
    if prev_next_row:
        keyboard.append(prev_next_row)

    # Row for New and Stop buttons
    keyboard.append([
        InlineKeyboardButton(
            '\U0001F5D1 ' + i18n.t("addarr.General.New"),
            callback_data=i18n.t("addarr.General.New")
        ),
        InlineKeyboardButton(
            '\U0001F6D1 ' + i18n.t("addarr.General.Stop"),
            callback_data=i18n.t("addarr.General.Stop")
        ),
    ])

    markup = InlineKeyboardMarkup(keyboard)

    # Send the message with the inline keyboard

    if choice == i18n.t("addarr.General.Movie"):
        message=i18n.t("addarr.Messages.This", subjectWithArticle=i18n.t("addarr.General.MovieWithArticle").lower())
    else:
        message=i18n.t("addarr.Messages.This", subjectWithArticle=i18n.t("addarr.General.SeriesWithArticle").lower())
   
    msg = await context.bot.send_message(
        chat_id=update.effective_message.chat_id, text=message, reply_markup=markup
    )
    # msg = await update.message.reply_text(message, reply_markup=markup)

    context.user_data["title_update_msg"] = context.user_data["update_msg"]
    context.user_data["update_msg"] = msg.message_id
    
    return GIVE_OPTION


async def nextOption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    position = min(context.user_data["position"] + 1, len(context.user_data["output"]) - 1)
    context.user_data["position"] = position
    searchResult = context.user_data["output"]
    choice = context.user_data["choice"]    

    message=i18n.t("addarr.SearchResults", count=len(searchResult))
    message += f"\n\n*{context.user_data['output'][position]['title']} ({context.user_data['output'][position]['year']})*"

    await context.bot.edit_message_text(
        message_id=context.user_data["title_update_msg"],
        chat_id=update.effective_message.chat_id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
    )

    keyboard = [
        [
            InlineKeyboardButton(
                '\U00002795 ' + i18n.t("addarr.Actions.Add"),
                callback_data=i18n.t("addarr.Actions.Add")
            ),
        ],
    ]

    # Row for Prev and Next buttons
    prev_next_row = []
    if position > 0:
        prev_next_row.append(
            InlineKeyboardButton(
                '\U000023EE ' + i18n.t("addarr.General.PreviousResult"),
                callback_data=i18n.t("addarr.General.PreviousResult")
            )
        )
    if position < len(context.user_data["output"]) - 1:
        prev_next_row.append(
            InlineKeyboardButton(
                '\U000023ED ' + i18n.t("addarr.General.NextResult"),
                callback_data=i18n.t("addarr.General.NextResult")
            )
        )

    # Add Prev/Next row only if it has buttons
    if prev_next_row:
        keyboard.append(prev_next_row)

    # Row for New and Stop buttons
    keyboard.append([
        InlineKeyboardButton(
            '\U0001F5D1 ' + i18n.t("addarr.General.New"),
            callback_data=i18n.t("addarr.General.New")
        ),
        InlineKeyboardButton(
            '\U0001F6D1 ' + i18n.t("addarr.General.Stop"),
            callback_data=i18n.t("addarr.General.Stop")
        ),
    ])

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
    if choice.lower() == i18n.t("addarr.General.Movie").lower():
        message=i18n.t("addarr.Messages.This", subjectWithArticle=i18n.t("addarr.General.MovieWithArticle").lower())
    else:
        message=i18n.t("addarr.Messages.This", subjectWithArticle=i18n.t("addarr.General.SeriesWithArticle").lower())
    msg = await context.bot.send_message(
        chat_id=update.effective_message.chat_id, text=message, reply_markup=markup
    )
    context.user_data["update_msg"] = msg.message_id
    return GIVE_OPTION


async def prevOption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    position = max(context.user_data["position"] - 1, 0)
    context.user_data["position"] = position
    searchResult = context.user_data["output"]
    choice = context.user_data["choice"]    

    message=i18n.t("addarr.SearchResults", count=len(searchResult))
    message += f"\n\n*{context.user_data['output'][position]['title']} ({context.user_data['output'][position]['year']})*"
    
    await context.bot.edit_message_text(
        message_id=context.user_data["title_update_msg"],
        chat_id=update.effective_message.chat_id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
    )
    
    keyboard = [
        [
            InlineKeyboardButton(
                '\U00002795 ' + i18n.t("addarr.Actions.Add"),
                callback_data=i18n.t("addarr.Actions.Add")
            ),
        ],
    ]

    # Row for Prev and Next buttons
    prev_next_row = []
    if position > 0:
        prev_next_row.append(
            InlineKeyboardButton(
                '\U000023EE ' + i18n.t("addarr.General.PreviousResult"),
                callback_data=i18n.t("addarr.General.PreviousResult")
            )
        )
    if position < len(context.user_data["output"]) - 1:
        prev_next_row.append(
            InlineKeyboardButton(
                '\U000023ED ' + i18n.t("addarr.General.NextResult"),
                callback_data=i18n.t("addarr.General.NextResult")
            )
        )

    # Add Prev/Next row only if it has buttons
    if prev_next_row:
        keyboard.append(prev_next_row)

    # Row for New and Stop buttons
    keyboard.append([
        InlineKeyboardButton(
            '\U0001F5D1 ' + i18n.t("addarr.General.New"),
            callback_data=i18n.t("addarr.General.New")
        ),
        InlineKeyboardButton(
            '\U0001F6D1 ' + i18n.t("addarr.General.Stop"),
            callback_data=i18n.t("addarr.General.Stop")
        ),
    ])

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
    if choice.lower() == i18n.t("addarr.General.Movie").lower():
        message=i18n.t("addarr.Messages.This", subjectWithArticle=i18n.t("addarr.General.MovieWithArticle").lower())
    else:
        message=i18n.t("addarr.Messages.This", subjectWithArticle=i18n.t("addarr.General.SeriesWithArticle").lower())
    msg = await context.bot.send_message(
        chat_id=update.effective_message.chat_id, text=message, reply_markup=markup
    )
    context.user_data["update_msg"] = msg.message_id
    return GIVE_OPTION


async def storeSelection(update : Update, context: ContextTypes.DEFAULT_TYPE):
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
        text=i18n.t("addarr.General.SelectAPath"),
        reply_markup=markup,
    )
    
    return GIVE_PATHS


async def storePath(update : Update, context: ContextTypes.DEFAULT_TYPE):
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
        return await storeQualityProfile(update, context)

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
        text=i18n.t("addarr.General.SelectAQuality"),
        reply_markup=markup,
    )

    return GIVE_QUALITY_PROFILES


async def storeQualityProfile(update : Update, context: ContextTypes.DEFAULT_TYPE):
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

    keyboard = [[InlineKeyboardButton('\U0001F5D3 ' + i18n.t("addarr.Actions.SelectedAndFutureSeasons"),callback_data="Season: Future and selected")]]
    for s in seasonNumbers:
        keyboard += [[
            InlineKeyboardButton(
                "\U00002705 " + f"{i18n.t('addarr.General.Season')} {s}",
                callback_data=f"Season: {s}"
            ),
        ]]
        selectedSeasons.append(int(s))

    keyboard += [[InlineKeyboardButton(i18n.t("addarr.Actions.DeselectAllSeasons"),callback_data=f"Season: None")]]

    markup = InlineKeyboardMarkup(keyboard)

    context.user_data["selectedSeasons"] = selectedSeasons

    await context.bot.edit_message_text(
        message_id=context.user_data["update_msg"],
        chat_id=update.effective_message.chat_id,
        text=i18n.t("addarr.General.SelectFromWhichSeason"),
        reply_markup=markup,
    )

    return SELECT_SEASONS


async def storeSeasons(update : Update, context: ContextTypes.DEFAULT_TYPE):
    choice = context.user_data["choice"]
    seasons = context.user_data["seasons"]
    selectedSeasons = []
    if "selectedSeasons" in context.user_data:
        selectedSeasons = context.user_data["selectedSeasons"]
 
    if choice.lower() == i18n.t("addarr.General.Series").lower():
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
                keyboard = [[InlineKeyboardButton('\U0001F5D3 ' + i18n.t("addarr.Actions.SelectedAndFutureSeasons"),callback_data="Season: Future and selected")]]
                for s in seasons:
                    if s in selectedSeasons: 
                        season = "\U00002705 " + f"{i18n.t('addarr.General.Season')} {s}" 
                    else:
                        season = "\U00002B1C " + f"{i18n.t('addarr.General.Season')} {s}"

                    keyboard.append([
                        InlineKeyboardButton(
                            season,
                            callback_data=f"Season: {s}"
                        )
                    ])
                
                if len(selectedSeasons) == len(seasons):
                    keyboard += [[InlineKeyboardButton(i18n.t("addarr.Actions.DeselectAllSeasons"),callback_data=f"Season: None")]]
                else:
                    keyboard += [[InlineKeyboardButton(i18n.t("addarr.Actions.SelectAllSeasons"),callback_data=f"Season: All")]]

                markup = InlineKeyboardMarkup(keyboard)

                await context.bot.edit_message_text(
                    message_id=context.user_data["update_msg"],
                    chat_id=update.effective_message.chat_id,
                    text=i18n.t("addarr.General.SelectFromWhichSeason"),
                    reply_markup=markup,
                )
                return SELECT_SEASONS
            
        if selectedSeasons is None:
            logger.debug(
                f"Callback query [{update.callback_query.data.replace('From season: ', '').strip()}] doesn't match any of the season options. Sending seasons for selection..."
            )
            return await storeSeasons(update, context) 


async def addMedia(update : Update, context: ContextTypes.DEFAULT_TYPE):
    position = context.user_data["position"]
    choice = context.user_data["choice"]
    idnumber = context.user_data["output"][position]["id"]
    path = context.user_data["path"]
    service = getService(context)
    service.setInstance(context.user_data["instance"])

    if choice.lower() == i18n.t("addarr.General.Series").lower():
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

    #create tag that will be used: userid
    
    if service_Config.get("addRequesterIdTag"):
        userTag = str(update.effective_message.chat.id)
        if service.tagExists(userTag) != -1:
            tags = [service.tagExists(userTag)]
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
        if choice.lower() == i18n.t("addarr.General.Movie").lower():
            added = service.addToLibrary(idnumber, path, qualityProfile, tags)
        else:
            added = service.addToLibrary(idnumber, path, qualityProfile, tags, seasonsSelected)
        
        if added:
            if choice.lower() == i18n.t("addarr.General.Movie").lower():
                message=i18n.t("addarr.Messages.AddSuccess", subjectWithArticle=i18n.t("addarr.General.MovieWithArticle"))
            else:
                message=i18n.t("addarr.Messages.AddSuccess", subjectWithArticle=i18n.t("addarr.General.SeriesWithArticle"))
            await context.bot.edit_message_text(
                message_id=context.user_data["update_msg"],
                chat_id=update.effective_message.chat_id,
                text=message,
            )
            if not checkAllowed(update,"admin") and config.get("adminNotifyId") is not None:
                adminNotifyId = config.get("adminNotifyId")
                if choice.lower() == i18n.t("addarr.General.Movie").lower():
                    message2=i18n.t("addarr.AdminNotifications.AddSuccess", subjectWithArticle=i18n.t("addarr.General.MovieWithArticle"),title=context.user_data['output'][position]['title'],first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
                else:
                    message2=i18n.t("addarr.AdminNotifications.AddSuccess", subjectWithArticle=i18n.t("addarr.General.SeriesWithArticle"),title=context.user_data['output'][position]['title'],first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
                await context.bot.send_message(
                    chat_id=adminNotifyId, text=message2
                )
            clearUserData(context)
            return ConversationHandler.END
        else:
            if choice.lower() == i18n.t("addarr.General.Movie").lower():
                message=i18n.t("addarr.Messages.AddFailed", subjectWithArticle=i18n.t("addarr.General.MovieWithArticle").lower())
            else:
                message=i18n.t("addarr.Messages.AddFailed", subjectWithArticle=i18n.t("addarr.General.SeriesWithArticle").lower())
            await context.bot.edit_message_text(
                message_id=context.user_data["update_msg"],
                chat_id=update.effective_message.chat_id,
                text=message,
            )
            if not checkAllowed(update,"admin") and config.get("adminNotifyId") is not None:
                adminNotifyId = config.get("adminNotifyId")
                if choice.lower() == i18n.t("addarr.General.Movie").lower():
                    message2=i18n.t("addarr.AdminNotifications.AddFailed", subjectWithArticle=i18n.t("addarr.General.MovieWithArticle"),title=context.user_data['output'][position]['title'],first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
                else:
                    message2=i18n.t("addarr.AdminNotifications.AddFailed", subjectWithArticle=i18n.t("addarr.General.SeriesWithArticle"),title=context.user_data['output'][position]['title'],first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
                await context.bot.send_message(
                    chat_id=adminNotifyId, text=message2
                )
            clearUserData(context)
            return ConversationHandler.END
    else:
        if choice.lower() == i18n.t("addarr.General.Movie").lower():
            message=i18n.t("addarr.Messages.Exist", subjectWithArticle=i18n.t("addarr.General.MovieWithArticle"))
        else:
            message=i18n.t("addarr.Messages.Exist", subjectWithArticle=i18n.t("addarr.General.SeriesWithArticle"))
        await context.bot.edit_message_text(
            message_id=context.user_data["update_msg"],
            chat_id=update.effective_message.chat_id,
            text=message,
        )
            
        if not checkAllowed(update,"admin") and config.get("adminNotifyId") is not None:
            adminNotifyId = config.get("adminNotifyId")
            if choice.lower() == i18n.t("addarr.General.Movie").lower():
                message2=i18n.t("addarr.AdminNotifications.Exist", subjectWithArticle=i18n.t("addarr.General.MovieWithArticle"),title=context.user_data['output'][position]['title'],first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
            else:
                message2=i18n.t("addarr.AdminNotifications.Exist", subjectWithArticle=i18n.t("addarr.General.SeriesWithArticle"),title=context.user_data['output'][position]['title'],first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
            await context.bot.send_message(
                chat_id=adminNotifyId, text=message2
            )
        clearUserData(context)
        return ConversationHandler.END

async def addNotificationChannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END
    
    subbed = await checkNotificationSubscribed(update.effective_message.chat_id)
    if subbed:
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.Notifications.ProfileExists"),
        )
        return
    
    await context.bot.send_message(
        chat_id=update.effective_message.chat_id, 
        text=i18n.t("addarr.Notifications.CreatingProfiles")
    )
    # add notifications to each instance. check each instance before adding. use chatID as profileName
    # check radarr and sonarr as well
    radarr_instances = config['radarr']['instances']
    sonarr_instances = config['sonarr']['instances']

    chatId = update.effective_message.chat_id

    for instance in radarr_instances:
        radarr.setInstance(instance["label"])
        if not radarr.notificationProfileExist(chatId):
            # create new
            profileName = await generateProfileName(context, chatId)
            status = radarr.createNotificationProfile(profileName, update.effective_chat.id)
            if status:
                label = instance["label"]
                logger.info(f"Successfully created notification profiles for Radarr instance {label}")
    
        
    for instance in sonarr_instances:
        sonarr.setInstance(instance["label"])
        if not sonarr.notificationProfileExist(chatId):
            # create new
            profileName = await generateProfileName(context, chatId)
            status = sonarr.createNotificationProfile(profileName, update.effective_chat.id)
            if status:
                label = instance["label"]
                logger.info(f"Successfully created notification profiles for Sonarr instance {label}")

    await context.bot.send_message(
        chat_id=update.effective_message.chat_id,
        text=i18n.t("addarr.Notifications.ProfileCreated"),
    )

async def help(update : Update, context: ContextTypes.DEFAULT_TYPE):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END
    
    helpText = i18n.t("addarr.Help",
            help=config["entrypointHelp"],
            authenticate=config["entrypointAuth"],
            add=config["entrypointAdd"],
            delete=config["entrypointDelete"],
            movie=i18n.t("addarr.General.Movie").lower(),
            serie=i18n.t("addarr.General.Series").lower(),
            allSeries=config["entrypointAllSeries"],
            allMovies=config["entrypointAllMovies"],
            transmission=config["entrypointTransmission"],
            sabnzbd=config["entrypointSabnzbd"],
            qbittorrent=config["entrypointqBittorrent"],
            notify=config["entrypointNotify"],
        )
    
    await context.bot.send_message(
        chat_id=update.effective_message.chat_id, 
        text=helpText,
        parse_mode=ParseMode.HTML

    )
    return ConversationHandler.END



if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    if loop.run_until_complete(startCheck()):
        main()
        loop.close()
    else:
        import sys
        sys.exit(0)
