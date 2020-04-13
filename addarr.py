#!/usr/bin/env python3

import datetime
import logging
import re
import time
import os

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
                             
SERIE_MOVIE_AUTHENTICATED, READ_CHOICE, GIVE_OPTION, TURTLE_NORMAL = range(4)

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
    auth_handler = CommandHandler('entrypointAuth', authentication)
    addMovieserie = ConversationHandler(
        entry_points=[CommandHandler(config['entrypointAdd'], startSerieMovie),
                      MessageHandler(Filters.regex(re.compile(r'' + config['entrypointAdd'] + '', re.IGNORECASE)), startSerieMovie)],

        states={
            SERIE_MOVIE_AUTHENTICATED: [MessageHandler(Filters.text, choiceSerieMovie)],
            READ_CHOICE: [MessageHandler(Filters.regex(f'^({transcript["Movie"]}|{transcript["Serie"]})$'), searchSerieMovie)],
            GIVE_OPTION: [MessageHandler(Filters.regex(f'({transcript["Add"]})'), addSerieMovie),
                          MessageHandler(Filters.regex(f'({transcript["Next result"]})'), nextOption),
                          MessageHandler(Filters.regex(f'({transcript["New"]})'), startSerieMovie)]
        },

        fallbacks=[CommandHandler('stop', stop),
                    MessageHandler(Filters.regex('^(Stop|stop)$'), stop)]
    )
    changeTransmissionSpeed = ConversationHandler(
        entry_points=[CommandHandler(config['entrypointTransmission'], transmission),
                      MessageHandler(Filters.regex(re.compile(r'' + config['entrypointTransmission'] + '', re.IGNORECASE)), transmission)],

        states={
            TURTLE_NORMAL: [MessageHandler(Filters.text, changeSpeedTransmission)]
        },

        fallbacks=[CommandHandler('stop', stop),
                    MessageHandler(Filters.regex('^(Stop|stop)$'), stop)]
    )

    dispatcher.add_handler(auth_handler)
    dispatcher.add_handler(addMovieserie)
    dispatcher.add_handler(changeTransmissionSpeed)
    print(transcript["Start chatting"])
    updater.start_polling()
    updater.idle()

#Check if Id is authenticated
def checkId(update):
    authorize=False
    with open(CHATID_PATH, 'r') as file:
        firstChar = file.read(1)
        if not firstChar:
            return False
        file.close()
    with open(CHATID_PATH, 'r') as file:
        for line in file:
            if line.strip("\n") == str(update.effective_message.chat_id):
                authorize=True
        file.close()
        if authorize:
            return True
        else:
            return False

def transmission(update, context,):
    if config["transmission"]["enable"]:
        if checkId(update):
            reply_keyboard = [[transcript["Transmission"]["Turtle"], transcript["Transmission"]["Normal"]]]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            update.message.reply_text(transcript["Transmission"]["Speed"], reply_markup=markup)
            return TURTLE_NORMAL
        else:
            context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["Authorize"])
            return TURTLE_NORMAL
    else :
        context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["Transmission"]["NotEnabled"])
        return ConversationHandler.END

def changeSpeedTransmission(update, context):
    if not checkId(update):
        if authentication(update, context) == "added": #To also stop the beginning command
            return ConversationHandler.END
    else:
        choice = update.message.text
        if choice == transcript["Transmission"]["Turtle"]:
            if config["transmission"]["authentication"]:
                auth = " --auth " + config["transmission"]["username"] + ":" + config["transmission"]["password"]
            os.system('transmission-remote ' + config["transmission"]["host"] + auth + " --alt-speed")
            context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["Transmission"]["ChangedToTurtle"])
            return ConversationHandler.END

        elif choice == transcript["Transmission"]["Normal"]:
            if config["transmission"]["authentication"]:
                auth = " --auth " + config["transmission"]["username"] + ":" + config["transmission"]["password"]
            os.system('transmission-remote ' + config["transmission"]["host"] + auth + " --no-alt-speed")
            context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["Transmission"]["ChangedToNormal"])
            return ConversationHandler.END

def authentication(update, context):
    password = update.message.text
    chatid=update.effective_message.chat_id
    if password == config["telegram"]["password"]:
        with open(CHATID_PATH, 'a') as file:
            file.write(str(chatid) + '\n')
            context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["Chatid added"])
            file.close()
        return "added"
    else:
        with open(LOG_PATH, 'a') as file:
            ts = time.time()
            sttime = datetime.datetime.fromtimestamp(ts).strftime('%d%m%Y_%H:%M:%S - ')
            file.write(sttime + '@'+str(update.message.from_user.username) + ' - ' + str(password) + '\n')
            file.close()
        context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["Wrong password"])
        return ConversationHandler.END #This only stops the auth conv, so it goes back to choosing screen

def stop(update, context):
    context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["End"])
    return ConversationHandler.END

def startSerieMovie(update, context):
    if checkId(update):
        context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["Title"])
        return SERIE_MOVIE_AUTHENTICATED
    else:
        context.bot.send_message(chat_id=update.effective_message.chat_id, text=transcript["Authorize"])
        return SERIE_MOVIE_AUTHENTICATED

def choiceSerieMovie(update, context):
    if not checkId(update):
        if authentication(update, context) == "added": #To also stop the beginning command
            return ConversationHandler.END
    else:
        text = update.message.text
        context.user_data['title'] = text
        reply_keyboard = [[transcript["Movie"], transcript["Serie"]]]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text(transcript["What is this?"], reply_markup=markup)
        return READ_CHOICE

def searchSerieMovie(update, context):
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


def nextOption(update, context):
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

def addSerieMovie(update, context):
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
