from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, InlineQueryHandler
from telegram import InlineQueryResultArticle, InputTextMessageContent, ReplyKeyboardMarkup
import telegram
import logging
import datetime
import requests
import json
import os

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)


TOKEN = "1109743971:AAGODNNc2dUo8aFBbEO9UHBXOtz5ae5htDA"
URL = "https://dog.ceo/api/breeds/image/random"
MUSIC_DIR = "/home/viet/Music"

def get_dog_img():
    r = requests.get(url=URL)
    data = json.loads(r.text)
    return data["message"]

def download_music(update, context):
    files = os.listdir(MUSIC_DIR)
    respond = "Please select file to download !\n"
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.ChatAction.TYPING)
    context.bot.send_message(chat_id=update.effective_chat.id, text=respond)
    for index, file in enumerate(files):
       respond = f"{index+1}. {file}\n"
       context.bot.send_message(chat_id=update.effective_chat.id, text=respond)


def start(update, context):
    respond = f"Hi, {update.effective_chat.username}. Are you a 0 or a 1 ?"
    keyboard = ['0', '1']
    markup = ReplyKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text=respond, reply_markup=markup)

def echo_back(update, context):
    user_message = update.message
    if user_message.text.lower() == "bye":
        respond = "Good bye."
    elif 'time' in user_message.text.lower():
        respond = f"It's {datetime.datetime.now()}"
    elif user_message.photo:
        respond = "Nice photo"
    else:
        respond = f"You said '{update.message.text}'"
    context.bot.send_message(chat_id=update.effective_chat.id, text=respond)

def caps(update, context):
    respond = f"To caps: {' '.join(context.args).upper()}"
    context.bot.send_message(chat_id=update.effective_chat.id, text=respond)

def inline_caps(update, context):
    query = update.inline_query.query
    if not query:
        return
    results = list()
    results.append(InlineQueryResultArticle(id=query.upper(), title='Caps', input_message_content=InputTextMessageContent(query.upper())))
    context.bot.answer_inline_query(chat_id=update.inline_query.id, text=results)

def dog(update, context):
    dog_img = get_dog_img()
    context.bot.send_message(chat_id=update.effective_chat.id, text=dog_img)

def help(update, context):
    respond = f"""This is Mr Rose Bot.\n/start - start Mr Rose Bot.\n/caps - turn text to CAPS"""
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=respond, text=None)

def main():
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    inline_caps_handler = InlineQueryHandler(inline_caps)
    dog_handler = CommandHandler('dog', dog)
    help_handler = CommandHandler('help', help)
    download_music_handler = CommandHandler('download_music', download_music)
    echo_back_handler = MessageHandler(Filters.text, echo_back)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(inline_caps_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(dog_handler)
    dispatcher.add_handler(download_music_handler)

    dispatcher.add_handler(echo_back_handler)
    updater.start_polling()

if __name__=='__main__':
    main()
