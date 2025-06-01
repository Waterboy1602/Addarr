from telegram.ext import ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import logging
import logger

from commons import authentication, checkAllowed, checkId, format_long_list_message, getService
from config import config
from translations import i18n

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.radarr", logLevel, config.get("logToConsole", False))

LS_GIVE_MOVIE_INSTANCE, LS_GIVE_SERIE_INSTANCE, GG_STATE = range(3)


async def startAllSeries(update, context):
    # check and authenticate user
    if config.get("enableAllowlist") and not checkAllowed(update, "regular"):
        # When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END

    if not checkId(update):
        if (
            await authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END
    else:
        # prompt for sonarr instance selection
        context.user_data["choice"] = i18n.t("addarr.General.Series")
        result = await selectInstance(update, context)
        if result == "one_instance":
            return await sendAll(update, context)
        return LS_GIVE_SERIE_INSTANCE


async def sendAll(update, context):
    if update.callback_query is not None:
        reply = update.callback_query.data.replace("instance=", "", 1)
        context.user_data["instance"] = reply

    instance = context.user_data["instance"]
    service = getService(context)
    service.setInstance(instance)

    if service.config.get("adminRestrictions") and not checkAllowed(update, "admin"):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.Authorization.NotAdmin"),
        )
        return ConversationHandler.END

    if not config.get("update_msg"):
        msg = await context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.Messages.LoadingAll"),
        )
        context.user_data["update_msg"] = msg.message_id
    else:
        await context.bot.edit_message_text(
            message_id=context.user_data["update_msg"],
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.Messages.LoadingAll"),
        )

    # show all series
    result = service.getAllMedia()
    content = format_long_list_message(result)

    if isinstance(content, str):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=content,
        )
    else:
        for subString in content:
            await context.bot.send_message(
                chat_id=update.effective_message.chat_id,
                text=subString,
            )
    return ConversationHandler.END


async def startAllMovies(update, context):
    # check and authenticate user
    if config.get("enableAllowlist") and not checkAllowed(update, "regular"):
        # When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END

    if not checkId(update):
        if (
            await authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END
    else:
        # prompt for sonarr instance selection
        context.user_data["choice"] = i18n.t("addarr.General.Movie")
        result = await selectInstance(update, context)
        if result == "one_instance":
            return await sendAll(update, context)
        return LS_GIVE_MOVIE_INSTANCE


async def selectInstance(update : Update, context):
    service_name = 'radarr' if context.user_data["choice"].lower() == i18n.t("addarr.General.Movie").lower() else 'sonarr'
    instances = config[service_name]["instances"]
    if len(instances) == 1:
        # There is only 1 instance, so use it!
        logger.debug(f"Only found 1 instance of {service_name}, so proceeding with that one...")
        context.user_data["instance"] = instances[0]["label"]
        return "one_instance"  # skip to next step
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

    msg = await update.effective_chat.send_message(
        text=i18n.t("addarr.General.SelectAnInstance"),
        reply_markup=markup
    )
    context.user_data["update_msg"] = msg.message_id
    return
