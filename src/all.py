from telegram.ext import ConversationHandler
import logging
import logger

from commons import authentication, checkAllowed, checkId, format_long_list_message
from config import config
from translations import i18n
import radarr as radarr
import sonarr as sonarr
import lidarr as lidarr

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.radarr", logLevel, config.get("logToConsole", False))


async def allSeries(update, context):
    logger.debug("allSeries() called")
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END

    if sonarr.config.get("adminRestrictions") and not checkAllowed(update,"admin"):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.NotAdmin"),
        )
        return ConversationHandler.END

    if not checkId(update):
        if (
            await authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END
    else:
        result = sonarr.allSeries()
        content = format_long_list_message(result)

        if isinstance(content, str):
            await context.bot.send_message(
                chat_id=update.effective_message.chat_id,
                text=content,
            )
        else:
            # print every substring
            for subString in content:
                await context.bot.send_message(
                    chat_id=update.effective_message.chat_id,
                    text=subString,
                )
        return ConversationHandler.END


async def allMovies(update, context):
    logger.debug("allMovies() called")
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END

    if radarr.config.get("adminRestrictions") and not checkAllowed(update,"admin"):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.NotAdmin"),
        )
        return ConversationHandler.END

    if not checkId(update):
        if (
            await authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END
    else:
        result = radarr.all_movies()
        content = format_long_list_message(result)

        if isinstance(content, str):
            await context.bot.send_message(
                chat_id=update.effective_message.chat_id,
                text=content,
            )
        else:
            # print every substring
            for subString in content:
                await context.bot.send_message(
                    chat_id=update.effective_message.chat_id,
                    text=subString,
                )
        return ConversationHandler.END


async def allMusic(update, context):
    logger.debug("allMusic() called")
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END

    if lidarr.config.get("adminRestrictions") and not checkAllowed(update,"admin"):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.NotAdmin"),
        )
        return ConversationHandler.END

    if not checkId(update):
        if (
            await authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END
    else:
        result = lidarr.allArtists()
        content = format_long_list_message(result)

        if isinstance(content, str):
            await context.bot.send_message(
                chat_id=update.effective_message.chat_id,
                text=content,
            )
        else:
            # print every substring
            for subString in content:
                await context.bot.send_message(
                    chat_id=update.effective_message.chat_id,
                    text=subString,
                )
        return ConversationHandler.END