#!/usr/bin/env python3

import datetime
import logging
import re
import time

import yaml
from telegram import *
from telegram.ext import *

import radarr as radarr
import sonarr as sonarr
from definitions import CONFIG_PATH, LANG_PATH, CHATID_PATH, LOG_PATH

log = logging
log.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename=LOG_PATH,
                filemode='a',
                             level=logging.INFO)
                             
SERIE_MOVIE_AUTH, READ_CHOICE, GIVE_OPTION = range(3)

config = yaml.safe_load(open(CONFIG_PATH, encoding='utf8'))

updater = Updater(config['telegram']['token'], use_context=True)
dispatcher = updater.dispatcher
lang = config["language"]

transcript = yaml.safe_load(open(LANG_PATH, encoding='utf8'))
transcript = transcript[lang]

output = None
service = None
    
def main():
    open(LOG_PATH, 'w').close() #clear logfile at startup of script
    auth_handler = CommandHandler('auth', auth)
    conversationHandler = ConversationHandler(
        entry_points=[CommandHandler(config['entrypoint'], start),
                      MessageHandler(Filters.regex(re.compile(r'' + config['entrypoint'] + '', re.IGNORECASE)), start)],

        states={
            SERIE_MOVIE_AUTH: [MessageHandler(Filters.text, choiceSerieMovie)],
            READ_CHOICE: [MessageHandler(Filters.regex(f'^({transcript["Movie"]}|{transcript["Serie"]})$'), search)],
            GIVE_OPTION: [MessageHandler(Filters.regex(f'({transcript["Add"]})'), add),
                          MessageHandler(Filters.regex(f'({transcript["Next result"]})'), nextOpt),
                          MessageHandler(Filters.regex(f'({transcript["New"]})'), start)],
        },

        fallbacks=[CommandHandler('stop', stop),
                    MessageHandler(Filters.regex('^(Stop|stop)$'), stop)]
    )
    dispatcher.add_handler(conversationHandler)
    dispatcher.add_handler(auth_handler)
    print(transcript["Start chatting"])
    updater.start_polling()
    updater.idle()

def auth(update, context):
    password = update.message.text
    chatid=update.effective_message.chat_id
    if password == config["telegram"]["password"]:
        with open(CHATID_PATH, 'a') as file:
            file.write(str(chatid) + '\n')
            context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["Chatid added"])
            file.close()
            start(update, context)
    else:
        with open(LOG_PATH, 'a') as file:
            ts = time.time()
            sttime = datetime.datetime.fromtimestamp(ts).strftime('%d%m%Y_%H:%M:%S - ')
            file.write(sttime + '@'+str(update.message.from_user.username) + ' - ' + str(password) + '\n')
            file.close()
        context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["Wrong password"])
        return ConversationHandler.END


def stop(update, context):
    context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["End"])
    return ConversationHandler.END


def start(update, context):
    authorize=False
    with open(CHATID_PATH, 'r') as file:
        firstChar = file.read(1)
        if not firstChar:
            context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["Authorize"])
            return SERIE_MOVIE_AUTH
        file.close()
    with open(CHATID_PATH, 'r') as file:
        for line in file:
            if line.strip("\n") == str(update.effective_message.chat_id):
                authorize=True
        file.close()
        if authorize:
            context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["Title"])
            return SERIE_MOVIE_AUTH
        else:
            context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["Authorize"])
            return SERIE_MOVIE_AUTH



def choiceSerieMovie(update, context):
    authorized=False
    with open(CHATID_PATH, 'r') as file:
        for line in file:
            if line.strip("\n") == str(update.effective_message.chat_id):
                authorized=True
        file.close()
        if not authorized:
            auth(update, context)
        else:
            text = update.message.text
            context.user_data['title'] = text
            reply_keyboard = [[transcript["Movie"], transcript["Serie"]]]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            update.message.reply_text(transcript["What is this?"], reply_markup=markup)
            return READ_CHOICE

def search(update, context):
    title = context.user_data['title']
    del context.user_data['title']
    choice = update.message.text
    context.user_data['choice'] = choice
    context.user_data['position'] = 0
    
    global service
    if choice == transcript["Serie"]:
        service = sonarr
    elif choice == transcript["Movie"]:
        service = radarr
    
    global output
    position = context.user_data['position']
    output = service.giveTitles(service.search(title))        

    reply_keyboard = [[transcript[choice.lower()]["Add"], transcript["Next result"]],
                        [transcript["New"], transcript["Stop"]]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript[choice.lower()]["This"])
    context.bot.sendPhoto(chat_id=update.effective_message.chat_id, photo=output[position]['poster'])
    text = output[position]['title'] + " (" + str(output[position]['year']) +  ")"
    context.bot.send_message(chat_id=update.effective_message.chat_id, text=text, reply_markup=markup)
    return GIVE_OPTION


def nextOpt(update, context):
    position = context.user_data['position'] + 1
    context.user_data['position'] = position

    choice = context.user_data['choice']

    if position < len(output):
        reply_keyboard = [[transcript[choice.lower()]["Add"], transcript["Next result"]],
                            [transcript["New"], transcript["Stop"]]]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

        context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript[choice.lower()]["This"])
        context.bot.sendPhoto(chat_id=update.effective_message.chat_id, photo=output[position]['poster'])
        text = output[position]['title'] + " (" + str(output[position]['year']) +  ")"
        context.bot.send_message(chat_id=update.effective_message.chat_id, text=text, reply_markup=markup)
        return GIVE_OPTION
    else:
        context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["No results"], reply_markup=markup)
        return stop()

def add(update, context):
    position = context.user_data['position']
    choice = context.user_data['choice']
    idnumber = output[position]['id']

    if not service.inLibrary(idnumber):
        if service.addToLibrary(idnumber):
            context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript[choice.lower()]["Success"])
            return ConversationHandler.END
        else:
            context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript[choice.lower()]["Failed"])
            return ConversationHandler.END

    else:
        context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript[choice.lower()]["Exist"])
        return ConversationHandler.END
         
if __name__ == '__main__':
    main()
