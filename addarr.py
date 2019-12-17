#!/usr/bin/env python3

from telegram import *
from telegram.ext import *
import sonarr as sonarr
import radarr as radarr
import logging, json, os
import yaml

from definitions import CONFIG_PATH

log = logging
log.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='telegramBot.log',
                             filemode='w',
                             level=logging.INFO)
SERIE_MOVIE, READ_CHOICE, GIVE_OPTION = range(3)

config = yaml.safe_load(open(CONFIG_PATH))
updater = Updater(config['telegram']['token'], use_context=True)
dispatcher = updater.dispatcher

output = None
service = None
    
def main():
    conversationHandler = ConversationHandler(
        entry_points=[CommandHandler('start', start),
                        MessageHandler(Filters.regex('^(Start|start)$'), start)],

        states={
            SERIE_MOVIE: [MessageHandler(Filters.text, choiceSerieMovie)],
            READ_CHOICE: [MessageHandler(Filters.regex('^(Film|Serie)$'), search)],
            GIVE_OPTION: [MessageHandler(Filters.regex('(voeg|toe)'), add),
                           MessageHandler(Filters.regex('(volgende|volgend|resultaat)'), nextOpt),
                           MessageHandler(Filters.regex('(nieuwe|nieuw|zoekopdracht)'), search)],
        },

        fallbacks=[CommandHandler('stop', stop),
                    MessageHandler(Filters.regex('^(Stop|stop)$'), stop)]
    )
    dispatcher.add_handler(conversationHandler)
    print("Start chatting with Addarr in Telegram")
    updater.start_polling()
    updater.idle()

def stop(update, context):
    context.bot.send_message(chat_id=update.effective_message.chat_id, text="Het toevoegen van films of series is beëindigd.")
    return ConversationHandler.END


def start(update, context):
    context.bot.send_message(chat_id=update.effective_message.chat_id, text="Geef de titel:")
    return SERIE_MOVIE

def choiceSerieMovie(update, context):
    text = update.message.text
    context.user_data['title'] = text
    reply_keyboard = [['Film', 'Serie']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text("Is dit een film of een serie?", reply_markup=markup)
    return READ_CHOICE

def search(update, context):
    title = context.user_data['title']
    del context.user_data['title']
    choice = update.message.text
    context.user_data['choice'] = choice
    context.user_data['position'] = 0
    
    global service
    if choice == "Serie":
        service = sonarr
    elif choice == "Film":
        service = radarr
    
    global output
    position = context.user_data['position']
    output = service.giveTitles(service.search(title))        

    reply_keyboard = [["Ja, voeg deze " + choice.lower() + " toe", "Nee, toon me volgend resultaat"],
                        [ "Voer een nieuwe zoekopdracht uit", "Stop"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    context.bot.send_message(chat_id=update.effective_message.chat_id, text="Is dit de " + choice.lower() + " die je wilt toevoegen?")
    context.bot.sendPhoto(chat_id=update.effective_message.chat_id, photo=output[position]['poster'])
    text = output[position]['title'] + " (" + str(output[position]['year']) +  ")"
    context.bot.send_message(chat_id=update.effective_message.chat_id, text=text, reply_markup=markup)
    return GIVE_OPTION


def nextOpt(update, context):
    position = context.user_data['position'] + 1
    context.user_data['position'] = position

    choice = context.user_data['choice']

    if position < len(output):
        reply_keyboard = [["Ja, voeg deze " + choice.lower() + " toe", "Nee, toon me volgend resultaat"],
                                [ "Voer een nieuwe zoekopdracht uit", "Stop"]]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

        context.bot.send_message(chat_id=update.effective_message.chat_id, text="Is dit de " + choice.lower() + " die je wilt toevoegen?")
        context.bot.sendPhoto(chat_id=update.effective_message.chat_id, photo=output[position]['poster'])
        text = output[position]['title'] + " (" + str(output[position]['year']) +  ")"
        context.bot.send_message(chat_id=update.effective_message.chat_id, text=text, reply_markup=markup)
        return GIVE_OPTION
    else:
        context.bot.send_message(chat_id=update.effective_message.chat_id, text="Geen resultaten meer te tonen.", reply_markup=markup)
        return stop()

def add(update, context):
    position = context.user_data['position']
    choice = context.user_data['choice']
    idnumber = output[position]['id']

    if not service.inLibrary(idnumber):
        if service.addToLibrary(idnumber):
            context.bot.send_message(chat_id=update.effective_message.chat_id, text="De " + choice.lower() + " is met succes toegevoegd :)")
            return ConversationHandler.END
        else:
            context.bot.send_message(chat_id=update.effective_message.chat_id, text="Mislukt om de " + choice.lower() + " toe te voegen.")
            return ConversationHandler.END

    else:
        context.bot.send_message(chat_id=update.effective_message.chat_id, text="Deze " + choice.lower() + " is al toegevoegd aan Plex.")
        return ConversationHandler.END
         
if __name__ == '__main__':
    main()
