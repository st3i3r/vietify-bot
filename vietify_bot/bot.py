from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, InlineQueryHandler
from telegram import InlineQueryResultArticle, InputTextMessageContent, ReplyKeyboardMarkup, InlineKeyboardButton, \
    InlineKeyboardMarkup
from telegram.error import NetworkError
from telegram import ChatAction
from functools import wraps
from botocore.exceptions import ClientError
import logging
import requests
import json
import bs4Virus
import boto3
import configparser
from lxml.html import fromstring
from itertools import cycle
import youtubedl

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

config = configparser.ConfigParser()
config.read("../config.ini")

aws_id = config["aws"]["aws_access_key_id"]
aws_key = config["aws"]["aws_secret_access_key"]
bot_token = config["telegram"]['TOKEN']
dog_url = config["dog"]["DOG_URL"]
music_dir = config["default"]["music_dir"]
music_bucket_name = config["aws"]["music_bucket"]
rest_uri = config["aws"]["rest_uri"]


# Get proxies from free-proxy-list.net
def get_proxies():
    """Return a list of proxies"""

    url = "https://free-proxy-list.net/"
    response = requests.get(url)
    parser = fromstring(response.text)
    proxies = set()
    for i in parser.xpath("//tbody/tr")[:10]:
        if 'yes' in i[6].text:
            host = i[0].text
            port = i[1].text
            proxies.add("https://" + ":".join([host, port]))
    return proxies


# AWS things
def list_s3_music():
    """Return list of music files on s3 bucket"""

    s3 = boto3.resource("s3", aws_access_key_id=aws_id,
                        aws_secret_access_key=aws_key)

    music_bucket = s3.Bucket(music_bucket_name)
    data = []
    for file in music_bucket.objects.all():
        data.append(file.key)
    return data


def download_from_bucket(obj_name, bucket_name=music_bucket_name):
    """Download a file from music bucket"""

    s3 = boto3.client("s3", aws_access_key_id=aws_id,
                      aws_secret_access_key=aws_key)
    s3.download_file(bucket_name, obj_name, f"/tmp/{obj_name}")
    logging.info(f"Saved to /tmp/{obj_name}")


def upload_files_to_bucket(file_list):
    """Upload many files to s3 bucket"""

    try:
        for f in file_list:
            upload_to_bucket(file_path=f)
    except ClientError as e:
        logging.error(e)
        return False
    return True


def upload_to_bucket(file_path, bucket_name=music_bucket_name):
    """Upload a file to s3 bucket."""

    s3 = boto3.resource("s3", aws_access_key_id=aws_id,
                        aws_secret_access_key=aws_key)

    obj_name = file_path.split('/')[-1].replace(' ', '_').replace("'", "")
    try:
        logging.info(f"Uploading {obj_name}")
        s3.Bucket(bucket_name).upload_file(file_path, obj_name)
        logging.info(f"Uploaded {obj_name}")
    except ClientError as e:
        logging.error(e)
        return False
    return True


# Decorators
def send_upload_audio_action(func):
    """Send upload action while processing func command"""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.UPLOAD_AUDIO)
        return func(update, context, *args, **kwargs)

    return command_func


def send_upload_video_action(func):
    """Send upload action while processing func command"""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.UPLOAD_VIDEO)
        return func(update, context, *args, **kwargs)

    return command_func


def send_typing_action(func):
    """Send typing action while processing func command"""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        return func(update, context, *args, **kwargs)

    return command_func


def send_upload_photo_action(func):
    """Send typing action while processing func command"""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
        return func(update, context, *args, **kwargs)

    return command_func


def get_dog_img():
    """Return a dog image"""

    r = requests.get(url=dog_url)
    response = json.loads(r.text)
    return response["message"]


def main_menu_keyboard():
    keyboard = [[InlineKeyboardButton("Music", callback_data="music_menu"),
                 InlineKeyboardButton("Corona Virus", callback_data="corona_menu"),
                 InlineKeyboardButton("Dog Image", callback_data="dog_image")],
                [InlineKeyboardButton("Youtube Downloader", callback_data="youtube-dl")],
                [InlineKeyboardButton("Main Menu", callback_data="main_menu")]]

    return InlineKeyboardMarkup(keyboard)


def music_menu_keyboard():
    keyboard = [[InlineKeyboardButton("List all files", callback_data='list_all_files'),
                 InlineKeyboardButton("Browse", callback_data="music_list")],
                [InlineKeyboardButton("Main Menu", callback_data="main_menu")]]

    return InlineKeyboardMarkup(keyboard)


def youtube_menu_keyboard():
    keyboard = [[InlineKeyboardButton("Download Video", callback_data='download_video'),
                 InlineKeyboardButton("Download Audio", callback_data='download_audio')]]

    return InlineKeyboardMarkup(keyboard)


def music_list_keyboard(start=0, paginator=10):
    music_list = list_s3_music()

    keyboard = []
    files = list(map(lambda x: x.replace("_", " ").split(".")[0], music_list))

    if start + paginator > len(files):
        paginator = len(files) - start

    for index in range(start, start + paginator):
        keyboard.append([InlineKeyboardButton(str(files[index]), callback_data="music_" + str(index))])

    if paginator < len(music_list):
        keyboard.append([InlineKeyboardButton("Next", callback_data="next_page")])

    if start >= paginator:
        keyboard[-1].insert(0, InlineKeyboardButton("Back", callback_data="prev_page"))

    keyboard.append([InlineKeyboardButton("Music Menu", callback_data="music_menu")])

    return InlineKeyboardMarkup(keyboard)


def corona_menu_keyboard(country_list):
    keyboard = [[]]
    for country in country_list:
        keyboard[0].append(InlineKeyboardButton(str(country), callback_data="corona_" + str(country)))

    keyboard.append([InlineKeyboardButton("Back", callback_data="main_menu")])

    return InlineKeyboardMarkup(keyboard)


@send_upload_audio_action
def music(update, context):
    """upload music file with specified index
    to bot channel. """

    music_list = list_s3_music()
    index = int(context.args[0])
    context.chat_data['index'] = index
    context.chat_data['music_list'] = music_list
    upload_music_to_bot(update, context)


def list_all_files(update, context):
    query = update.callback_query

    music_list = list_s3_music()
    response = ""

    for index, file in enumerate(music_list):
        response += f"{index}. {file.replace('_', ' ')}\n"
        if index != 0 and index % 40 == 0:
            context.bot.send_message(chat_id=update.effective_chat.id, text=response)
            response = ""
        elif index > 40 * (len(music_list) / 40):
            pass

    context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    start_bot(update, context)


def main_menu(update, context):
    query = update.callback_query
    context.bot.edit_message_text(text="Main Menu",
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id,
                                  reply_markup=main_menu_keyboard())


def music_menu(update, context):
    query = update.callback_query
    context.bot.edit_message_text(text="S3 AWS Music Server",
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id,
                                  reply_markup=music_menu_keyboard())


def corona_menu(update, context):
    query = update.callback_query
    country_list = ["Vietnam", "Russia", "USA", "World", "Europe"]

    context.chat_data["country_list"] = country_list
    context.bot.edit_message_text(text="Get corona virus data.",
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id,
                                  reply_markup=corona_menu_keyboard(country_list))


# Callback button handlers
def callback_country_select(update, context):
    query = update.callback_query
    country = query.data.split("corona_")[-1]

    c = bs4Virus.VirusUpdater()
    country_list = context.chat_data["country_list"]

    context.bot.edit_message_text(text=c.get_by_country(country),
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id,
                                  reply_markup=corona_menu_keyboard(country_list))


def music_list(update, context):
    query = update.callback_query

    music_list = list_s3_music()

    context.chat_data["current_page"] = context.chat_data.get("current_page", 1)
    context.chat_data["paginator"] = 10
    context.chat_data["music_list"] = music_list
    context.chat_data["total_page"] = len(music_list) // context.chat_data["paginator"] + 1

    context.bot.edit_message_text(text=f"Page: {context.chat_data['current_page']}/{context.chat_data['total_page']}",
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id,
                                  reply_markup=music_list_keyboard(paginator=context.chat_data["paginator"]))


def next_music_page(update, context):
    query = update.callback_query

    context.chat_data["current_page"] += 1
    current_page = context.chat_data["current_page"]
    total_page = context.chat_data["total_page"]
    paginator = context.chat_data["paginator"]
    start_index = paginator * current_page

    context.bot.edit_message_text(text="Page: {}/{}".format(current_page, total_page),
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id,
                                  reply_markup=music_list_keyboard(start_index))


def prev_music_page(update, context):
    query = update.callback_query

    context.chat_data["current_page"] -= 1
    current_page = context.chat_data["current_page"]
    total_page = context.chat_data["total_page"]
    paginator = context.chat_data["paginator"]
    start_index = paginator * current_page

    context.bot.edit_message_text(text="Page: {}/{}".format(current_page, total_page),
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id,
                                  reply_markup=music_list_keyboard(start_index))


def callback_file_select(update, context):
    query = update.callback_query
    music_list = context.chat_data["music_list"]

    query.answer()
    query.edit_message_text(text="Uploading file ...")

    data = query.data
    index = int(data.split("_")[-1])

    context.chat_data["index"] = index
    context.chat_data["music_list"] = music_list
    upload_music_to_bot(update, context)


def download_audio(update, context):
    query = update.callback_query
    url = context.chat_data['url']
    logging.info(f"Downloading audio {url}")
    filename = youtubedl.download_audio(url)

    query.edit_message_text(f"Uploading audio {filename}")
    context.bot.send_audio(chat_id=update.effective_chat.id,
                           audio=open(f"/tmp/{filename}", 'rb'),
                           timeout=1000)


@send_upload_audio_action
def download_video(update, context):
    # query = update.callback_query
    # url = context.chat_data['url']
    # logging.info(f"Downloading video {url}")
    # filename = youtubedl.download_video(url)
    # logging.info(f"File saved to /tmp/{filename}")

    # query.edit_message_text(f"Uploading video {filename}")
    # context.bot.send_video(chat_id=update.effective_chat.id,
    #                        video=open(f"/tmp/{filename}", 'rb'),
    #                        timeout=200000)
    pass


@send_upload_audio_action
def upload_music_to_bot(update, context):
    files = context.chat_data["music_list"]
    index = int(context.chat_data["index"])
    download_from_bucket(files[index])

    context.bot.send_audio(chat_id=update.effective_chat.id,
                           audio=open(f'/tmp/{files[index]}', 'rb'),
                           timeout=1000)


def start_bot(update, context):
    response = f"Hi, {update.effective_chat.username}. Are you a 0 or a 1 ?"
    update.message.reply_text(text=response, reply_markup=main_menu_keyboard())


def echo_back(update, context):
    user_message = update.message
    if "bye" in user_message.text.lower():
        response = "Good bye."
    elif user_message.photo:
        response = "Nice photo"
    else:
        response = f"You said {repr(update.message.text)}"
    update.message.reply_text(text=response)


def inline_caps(update, context):
    query = update.inline_query.query
    if not query:
        return

    results = list()
    results.append(InlineQueryResultArticle(id=query.upper(),
                                            title='Caps',
                                            input_message_content=InputTextMessageContent(query.upper())))
    context.bot.answer_inline_query(chat_id=update.inline_query.id, text=results)


@send_upload_photo_action
def dog(update, context):
    query = update.callback_query
    dog_img = get_dog_img()

    context.bot.send_message(chat_id=update.effective_chat.id, text=dog_img)
    context.bot.send_message(chat_id=query.message.chat_id,
                             message_id=query.message.message_id,
                             text='Welcome to Mr Rose Bot !!! Are you a 0 or a 1 ?',
                             reply_markup=main_menu_keyboard())


def youtube_link_handle(update, context):
    url = update.message.text

    context.chat_data['url'] = url
    update.message.reply_text(text="Choose an option:", reply_markup=youtube_menu_keyboard())


def help_bot(update, context):
    response = "This is Mr Rose Bot.\n/start - start Mr Rose Bot.\n/caps - turn text to CAPS."
    context.bot.send_message(chat_id=update.effective_chat.id, text=response)


def unknown(update, context):
    response = "Sorry, I didn't understand that command."
    context.bot.send_message(chat_id=update.effective_chat.id, text=response)


def callback_welcome(context):
    context.bot.send_message(chat_id='@pwn40_chan', text="Welcome to Mr Rose Bot Machine.")


def callback_alarm(context):
    context.bot.send_message(chat_id=context.job.context,
                             text="BEEP BEEP BEEP")


def set_timer(update, context):
    user_timer = (context.args and int(context.args[0])) or 30
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"Setting alarm in {user_timer} secs.")

    context.job_queue.run_once(callback_alarm, user_timer, context=update.message.chat_id)


def main(proxy=None):
    logging.info("Running main func.")
    request_kwargs = {'proxy_url': proxy}
    updater = Updater(token=bot_token, use_context=True, request_kwargs=request_kwargs)
    dispatcher = updater.dispatcher
    j_queue = updater.job_queue

    start_handler = CommandHandler('start', start_bot)
    inline_caps_handler = InlineQueryHandler(inline_caps)
    dog_handler = CallbackQueryHandler(dog, pattern="dog_image")
    help_handler = CommandHandler('help', help_bot)
    music_handler = CommandHandler('music', music)
    main_menu_handler = CallbackQueryHandler(main_menu, pattern='main_menu')
    music_menu_handler = CallbackQueryHandler(music_menu, pattern='music_menu')
    corona_handler = CallbackQueryHandler(corona_menu, pattern="corona_menu")
    set_timer_handler = CommandHandler('timer', set_timer)
    unknown_handler = MessageHandler(Filters.command, unknown)
    echo_back_handler = MessageHandler(Filters.text, echo_back)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(inline_caps_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(dog_handler)
    dispatcher.add_handler(music_handler)
    dispatcher.add_handler(main_menu_handler)

    dispatcher.add_handler(music_menu_handler)
    dispatcher.add_handler(CallbackQueryHandler(list_all_files, pattern="list_all_files"))
    dispatcher.add_handler(CallbackQueryHandler(music_list, pattern="music_list"))
    dispatcher.add_handler(CallbackQueryHandler(callback_file_select, pattern="^music_[0-9]+$"))
    dispatcher.add_handler(CallbackQueryHandler(next_music_page, pattern="next_page"))
    dispatcher.add_handler(CallbackQueryHandler(prev_music_page, pattern="prev_page"))

    dispatcher.add_handler(corona_handler)
    dispatcher.add_handler(CallbackQueryHandler(callback_country_select, pattern="^corona_[a-zA-Z]+$"))

    dispatcher.add_handler(MessageHandler(Filters.regex('youtu.be|youtube.com'), youtube_link_handle))
    dispatcher.add_handler(CallbackQueryHandler(download_audio, pattern='download_audio'))
    dispatcher.add_handler(CallbackQueryHandler(download_video, pattern='download_video'))

    dispatcher.add_handler(set_timer_handler)
    dispatcher.add_handler(unknown_handler)
    dispatcher.add_handler(echo_back_handler)

    j_minute = j_queue.run_repeating(callback_welcome, interval=30, first=0)
    j_minute.enabled = False

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    #  files = os.listdir('/home/viet/Music')
    #  file_list = list(map(lambda x: os.path.join(music_dir, x), files))
    #  upload_files_to_bucket(file_list[120:140])

    logging.info("Getting proxy list.")
    proxies = get_proxies()
    proxy_pool = cycle(proxies)

    while True:
        try:
            proxy = next(proxy_pool)
            logging.info("Using proxy: {}".format(proxy))
            main(proxy=None)
        except NetworkError:
            continue
