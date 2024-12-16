import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from commons import authentication, checkAllowed, checkId, generateServerAddr
from config import config
from translations import i18n
import logging
import logger

# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.radarr", logLevel, config.get("logToConsole", False))

config = config["qbittorrent"]

QBITTORRENT_SPEED_ALTERNATE,  QBITTORRENT_SPEED_NORMAL= range(2)

async def qbittorrent(update, context):
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
            chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Authorize")
        )
        return QBITTORRENT_SPEED_NORMAL
    if config["onlyAdmin"] and not checkAllowed(update, "admin"):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.NotAdmin"),
        )
        return QBITTORRENT_SPEED_NORMAL

    keyboard = [[
        InlineKeyboardButton(
            '\U0001F40C ' + i18n.t("addarr.qBittorrent.Alternate"),
            callback_data= QBITTORRENT_SPEED_ALTERNATE
        ),
        InlineKeyboardButton(
            '\U0001F40E ' + i18n.t("addarr.qBittorrent.Normal"),
            callback_data= QBITTORRENT_SPEED_NORMAL
        ),
    ]]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        i18n.t("addarr.qBittorrent.Speed"), reply_markup=markup
    )
    return QBITTORRENT_SPEED_NORMAL

async def changeSpeedqBittorrent(update, context):
    if not checkId(update):
        if (
            await authentication(update, context) == "added"
        ):  # To also stop the beginning command
            return ConversationHandler.END

    choice = update.callback_query.data

    session = requests.Session()
    url = generateServerAddr("qbittorrent") + "api/v2/auth/login"

    headers = {
        "Accept": "*/*",
        "User-Agent": "Addarr",
        "Referer": generateServerAddr("qbittorrent"),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    form_data = {"username": config["auth"]["username"], "password": config["auth"]["password"]}
    session.post(url, data=form_data, headers=headers)

    toggle_url = generateServerAddr("qbittorrent") + "api/v2/transfer/toggleSpeedLimitsMode"
    if int(choice) == QBITTORRENT_SPEED_ALTERNATE:
        form_data = {"mode": 1}
        toggle_response = session.post(toggle_url, headers=headers, data=form_data)
        if toggle_response.status_code == 200:
            message = i18n.t("addarr.qBittorrent.ChangedToAlternate")
        else:
            message = i18n.t("addarr.qBittorrent.Error")
        
    elif int(choice) == QBITTORRENT_SPEED_NORMAL:
        form_data = {"mode": 0}
        toggle_response = session.post(toggle_url, headers=headers, data=form_data)
        if toggle_response.status_code == 200:
            message = i18n.t("addarr.qBittorrent.ChangedToNormal")
        else:
            message = i18n.t("addarr.qBittorrent.Error")
        

    await context.bot.send_message(
        chat_id=update.effective_message.chat_id,
        text=message,
    )

    return ConversationHandler.END
