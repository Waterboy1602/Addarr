import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ConversationHandler, ContextTypes


from commons import authentication, checkAllowed, checkId, generateServerAddr, clearUserData
from config import config
from translations import i18n
import logging
import logger

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.radarr", logLevel, config.get("logToConsole", False))

config = config["qbittorrent"]

QBT_AUTHENTICATE, QBT_GIVE_SPEED_TYPES = range(2)

async def qbittorrent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END
        
    if not config["enable"]:
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.qBittorrent.NotEnabled"),
        )
        return ConversationHandler.END

    if not checkId(update):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Authorization.Authorize")
        )
        return QBT_AUTHENTICATE
    
    if config["onlyAdmin"] and not checkAllowed(update, "admin"):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.Authorization.NotAdmin"),
        )
        return QBT_AUTHENTICATE

    keyboard = [[
        InlineKeyboardButton(
            '\U0001F40C ' + i18n.t("addarr.qBittorrent.Alternate"),
            callback_data=f"speedtype={i18n.t('addarr.qBittorrent.Alternate')}"
        ),
        InlineKeyboardButton(
            '\U0001F40E ' + i18n.t("addarr.qBittorrent.Normal"),
            callback_data=f"speedtype={i18n.t('addarr.qBittorrent.Normal')}"
        ),
    ]]
    
    markup = InlineKeyboardMarkup(keyboard)
    msg = await update.message.reply_text(
        i18n.t("addarr.qBittorrent.Speed"), reply_markup=markup
    )
    context.user_data['qbit_msg'] = msg.message_id
    return QBT_GIVE_SPEED_TYPES

async def setClientSpeed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not checkId(update):
        if (
            await authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END

    if update.message is not None:
        reply = update.message.text.lower()
        logger.debug(f"reply is {reply}")
    elif update.callback_query is not None:
        reply = update.callback_query.data
    else:
        return QBT_AUTHENTICATE
    
    if not context.user_data.get("speedtype"):
        if reply.startswith("speedtype="):
            choice = reply.replace("speedtype=", "", 1)
        else:
            choice = reply
        context.user_data["speedtype"] = choice
        logger.debug(f"User wants to set {choice}")
    else:
        logger.debug("Instance set from previous function")

    choice = context.user_data["speedtype"]

    session = requests.Session()
    url = generateServerAddr("qbittorrent") + "api/v2/auth/login"

    headers = {
        "Accept": "*/*",
        "User-Agent": "Addarr",
        "Referer": generateServerAddr("qbittorrent"),
        "Content-Type": "application/x-www-form-urlencoded"
    }

    logger.debug('Sending request to qbittorrent')
    form_data = {"username": config["auth"]["username"], "password": config["auth"]["password"]}
    session.post(url, data=form_data, headers=headers)

    toggle_url = generateServerAddr("qbittorrent") + "api/v2/transfer/toggleSpeedLimitsMode"
    
    if choice == i18n.t("addarr.qBittorrent.Alternate"):
        logger.debug("setting alternate mode in form data")
        form_data = {"mode": 1}
        toggle_response = session.post(toggle_url, headers=headers, data=form_data)
        logger.debug(f"Response from qbit: {toggle_response}")
        if toggle_response.status_code == 200:
            message = i18n.t("addarr.qBittorrent.ChangedToAlternate")
        else:
            message = i18n.t("addarr.qBittorrent.Error")
        
    elif choice == i18n.t("addarr.qBittorrent.Normal"):
        logger.debug("setting normal mode in form data")
        form_data = {"mode": 0}
        toggle_response = session.post(toggle_url, headers=headers, data=form_data)
        logger.debug(f"Response from qbit: {toggle_response}")
        if toggle_response.status_code == 200:
            message = i18n.t("addarr.qBittorrent.ChangedToNormal")
        else:
            message = i18n.t("addarr.qBittorrent.Error")
        
    await context.bot.edit_message_text(
            message_id=context.user_data["qbit_msg"],
            chat_id=update.effective_message.chat_id,
            text=message,
    )

    clearUserData(context)
    return ConversationHandler.END
