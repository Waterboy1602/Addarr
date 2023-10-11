from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ConversationHandler

import logging
import logger

from commons import authentication, checkAllowed, checkId
from config import config
from translations import i18n
from addarr import getService, clearUserData, stop



# Set up logging
logLevel = logging.DEBUG if config.get("debugLogging", False) else logging.INFO
logger = logger.getLogger("addarr.radarr", logLevel, config.get("logToConsole", False))

SERIE_MOVIE_DELETE, READ_DELETE_CHOICE,GIVE_OPTION = range(3)

async def delete(update : Update, context):
    if config.get("enableAllowlist") and not checkAllowed(update,"regular"):
        #When using this mode, bot will remain silent if user is not in the allowlist.txt
        logger.info("Allowlist is enabled, but userID isn't added into 'allowlist.txt'. So bot stays silent")
        return ConversationHandler.END

    if not checkAllowed(update, "admin"):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.NotAdmin"),
        )
        return ConversationHandler.END

    if not checkId(update):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=i18n.t("addarr.Authorize")
        )
        return SERIE_MOVIE_DELETE
    
    if update.message is not None:
        reply = update.message.text.lower()
    elif update.callback_query is not None:
        reply = update.callback_query.data.lower()
    else:
        return SERIE_MOVIE_DELETE

    if reply == i18n.t("addarr.New").lower():
        logger.debug("User issued New command, so clearing user_data")
        clearUserData(context)
    
    await context.bot.send_message(
        chat_id=update.effective_message.chat_id, text='\U0001F3F7 '+i18n.t("addarr.Title")
    )
    if not checkAllowed(update,"admin") and config.get("adminNotifyId") is not None:
        adminNotifyId = config.get("adminNotifyId")
        message2=i18n.t("addarr.Notify.Delete", first_name=update.effective_message.chat.first_name, chat_id=update.effective_message.chat.id)
        msg2 = context.bot.send_message(
            chat_id=adminNotifyId, text=message2
    )
    return SERIE_MOVIE_DELETE
    

async def choiceDeleteSerieMovie(update, context):
    service = getService(context)
    if service.config.get("adminRestrictions") and not checkAllowed(update, context, "admin"):
        await context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text=i18n.t("addarr.NotAdmin"),
        )
        return ConversationHandler.END
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
        elif update.callback_query is not None:
            reply = update.callback_query.data
        else:
            return SERIE_MOVIE_DELETE

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
            return await deleteSerieMovie(update, context)
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
            msg = await update.message.reply_text(i18n.t("addarr.What is this?"), reply_markup=markup)
            context.user_data["update_msg"] = msg.message_id

        return READ_DELETE_CHOICE


async def confirmDelete(update, context):
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

    searchResult = service.search(title)
    if not searchResult:
        await context.bot.send_message( 
            chat_id=update.effective_message.chat_id, 
            text=i18n.t("addarr.searchresults", count=0),
        )
        clearUserData(context)
        return ConversationHandler.END
        
    context.user_data["output"] = service.giveTitles(searchResult)
    idnumber = context.user_data["output"][position]["id"]

    if service.inLibrary(idnumber):
        keyboard = [
                [
                    InlineKeyboardButton(
                        '\U00002795 '+i18n.t("addarr.Delete"),
                        callback_data=i18n.t("addarr.Delete")
                    ),
                ],[
                    InlineKeyboardButton(
                        '\U000023ED '+i18n.t("addarr.StopDelete"),
                        callback_data=i18n.t("addarr.Stop")
                    ),
                ],[ 
                    InlineKeyboardButton(
                        '\U0001F50D '+i18n.t("addarr.New"),
                        callback_data=i18n.t("addarr.New")
                    ),
                ]
            ]
        markup = InlineKeyboardMarkup(keyboard)
        
        message = f"\n\n*{context.user_data['output'][position]['title']} ({context.user_data['output'][position]['year']})*"
        
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
        
        img = await context.bot.sendPhoto(
            chat_id=update.effective_message.chat_id,
            photo=context.user_data["output"][position]["poster"],
        )
        context.user_data["photo_update_msg"] = img.message_id
        
        if choice == i18n.t("addarr.Movie"):
            message=i18n.t("addarr.messages.ThisDelete", subjectWithArticle=i18n.t("addarr.MovieWithArticle").lower())
        else:
            message=i18n.t("addarr.messages.ThisDelete", subjectWithArticle=i18n.t("addarr.SeriesWithArticle").lower())
        msg = await context.bot.send_message(
            chat_id=update.effective_message.chat_id, text=message, reply_markup=markup
        )
        context.user_data["title_update_msg"] = context.user_data["update_msg"]
        context.user_data["update_msg"] = msg.message_id
    else:
        if choice == i18n.t("addarr.Movie"):
            message=i18n.t("addarr.messages.NoExist", subjectWithArticle=i18n.t("addarr.MovieWithArticle"))
        else:
            message=i18n.t("addarr.messages.NoExist", subjectWithArticle=i18n.t("addarr.SeriesWithArticle"))
        await context.bot.edit_message_text(
            message_id=context.user_data["update_msg"],
            chat_id=update.effective_message.chat_id,
            text=message,
        )
        clearUserData(context)
        return ConversationHandler.END
    return GIVE_OPTION

async def deleteSerieMovie(update, context):  
    choice = context.user_data["choice"]  
    position = context.user_data["position"]
    service = getService(context)
    idnumber = context.user_data["output"][position]["id"]

    if service.removeFromLibrary(idnumber):
        if choice == i18n.t("addarr.Movie"):
            message=i18n.t("addarr.messages.DeleteSuccess", subjectWithArticle=i18n.t("addarr.MovieWithArticle"))
        else:
            message=i18n.t("addarr.messages.DeleteSuccess", subjectWithArticle=i18n.t("addarr.SeriesWithArticle"))
    else:
        if choice == i18n.t("addarr.Movie"):
            message=i18n.t("addarr.messages.DeleteFailed", subjectWithArticle=i18n.t("addarr.MovieWithArticle"))
        else:
            message=i18n.t("addarr.messages.DeleteFailed", subjectWithArticle=i18n.t("addarr.SeriesWithArticle"))
    await context.bot.edit_message_text(
            message_id=context.user_data["update_msg"],
            chat_id=update.effective_message.chat_id,
            text=message,
    )
    clearUserData(context)
    return ConversationHandler.END