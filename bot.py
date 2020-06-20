from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, InlineQueryHandler
from telegram.chataction import ChatAction
from telegram.error import NetworkError
from functools import wraps
from botocore.exceptions import ClientError
import os
import sys
import logging
import requests
import json
from CoronaVirusUpdater import bs4Virus
import boto3
import configparser
from lxml.html import fromstring
from itertools import cycle
from YoutubeDownloader import youtubedl
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

config = configparser.ConfigParser()
config.read("config.ini")

mode = os.getenv("MODE")

if mode == "dev":
    AWS_ID = config["aws"]["aws_access_key_id"]
    AWS_KEY = config["aws"]["aws_secret_access_key"]
    BOT_TOKEN = config["telegram"]['TOKEN']
    DOG_URL = config["dog"]["DOG_URL"]
    MUSIC_BUCKET_NAME = config["aws"]["music_bucket"]
    REST_URI = config["aws"]["rest_uri"]
    USE_PROXY = False


    def run(updater):
        logging.info(f"Running bot in dev mode.")
        updater.start_polling()
        #updater.idle()

elif mode == "prod":
    AWS_ID = os.environ.get("AWS_ID")
    AWS_KEY = os.environ.get("AWS_KEY")
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    DOG_URL = os.environ.get("DOG_URL")
    MUSIC_BUCKET_NAME = os.environ.get("MUSIC_BUCKET_NAME")
    REST_URI = os.environ.get("REST_URI")
    USE_PROXY = os.environ.get("USER_PROXY")


    def run(updater):
        logging.info(f"Running bot in prod mode.")
        PORT = os.environ.get("PORT", 8443)
        HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")

        updater.start_webhook(listen='0.0.0.0',
                              port=PORT,
                              url_path=BOT_TOKEN)
        updater.bot.setWebhook(f'https://{HEROKU_APP_NAME}.herokuapp.com/{BOT_TOKEN}')

else:
    logging.error("No mode specified.")
    sys.exit(1)


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

    s3 = boto3.resource("s3", aws_access_key_id=AWS_ID,
                        aws_secret_access_key=AWS_KEY)

    music_bucket = s3.Bucket(MUSIC_BUCKET_NAME)
    data = []
    for file in music_bucket.objects.all():
        data.append(file.key)
    return data


def download_from_bucket(obj_name, bucket_name=MUSIC_BUCKET_NAME):
    """Download a file from music bucket"""

    s3 = boto3.client("s3", aws_access_key_id=AWS_ID,
                      aws_secret_access_key=AWS_KEY)
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


def upload_to_bucket(file_path, bucket_name=MUSIC_BUCKET_NAME):
    """Upload a file to s3 bucket."""

    s3 = boto3.resource("s3", aws_access_key_id=AWS_ID,
                        aws_secret_access_key=AWS_KEY)

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

    r = requests.get(url=DOG_URL)
    response = json.loads(r.text)
    return response["message"]


def main_menu_keyboard():
    keyboard = [[InlineKeyboardButton("Music", callback_data="music_menu"),
                 InlineKeyboardButton("Corona Virus", callback_data="corona_menu"),
                 InlineKeyboardButton("Dog Image", callback_data="dog_image")],
                [InlineKeyboardButton("Youtube Downloader", callback_data="youtube-dl-help")]]

    return InlineKeyboardMarkup(keyboard)


def music_menu_keyboard():
    keyboard = [[InlineKeyboardButton("List all files", callback_data='list_all_files'),
                 InlineKeyboardButton("Browse", callback_data="music_list")],
                [InlineKeyboardButton("Main Menu", callback_data="main_menu")]]

    return InlineKeyboardMarkup(keyboard)


def youtube_menu_keyboard():
    keyboard = [[InlineKeyboardButton("Get video", callback_data='download_video'),
                 InlineKeyboardButton("Get audio", callback_data='download_audio')],
                [InlineKeyboardButton("Upload audio to S3 AWS", callback_data='youtube_audio_to_s3')],
                [InlineKeyboardButton("Upload video to S3 AWS", callback_data='youtube_video_to_s3')]]

    return InlineKeyboardMarkup(keyboard)


def music_list_keyboard(start=0, paginator=8):
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
    keyboard.append([InlineKeyboardButton("Main Menu", callback_data="main_menu")])

    return InlineKeyboardMarkup(keyboard)


def corona_menu_keyboard(country_list):
    keyboard = [[]]
    for country in country_list:
        keyboard[0].append(InlineKeyboardButton(str(country), callback_data="corona_" + str(country)))

    keyboard.append([InlineKeyboardButton("Manually update database", callback_data="update_corona_data")])
    keyboard.append([InlineKeyboardButton("Main Menu", callback_data="main_menu")])

    return InlineKeyboardMarkup(keyboard)


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

    query.edit_message_text("Fetching data ...")

    corona_data = {}
    for _country in country_list:
        if _country not in corona_data:
            corona_data[_country] = corona_updater.get_by_country(_country)

    context.chat_data['corona_data'] = corona_data
    context.chat_data['country_list'] = country_list

    context.bot.edit_message_text(text="Get corona virus data.",
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id,
                                  reply_markup=corona_menu_keyboard(country_list))


def list_all_files(update, context):
    query = update.callback_query

    music_list = list_s3_music()
    response = ""

    if context.args:
        index = int(context.args[0])
        response = f"Download link for {music_list[index]}: "
        response += ''.join([REST_URI, music_list[index]])

    else:
        for index, file in enumerate(music_list):
            response += f"{index}. {file.replace('_', ' ')}\n"
            if index != 0 and index % 40 == 0:
                context.bot.send_message(chat_id=update.effective_chat.id, text=response)
                response = ""
            elif index > 40 * (len(music_list) / 40):
                pass

    context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    # start_bot(update, context)


def music_list(update, context):
    query = update.callback_query

    music_list = list_s3_music()

    context.chat_data["current_page"] = context.chat_data.get("current_page", 1)
    context.chat_data["paginator"] = 8
    context.chat_data["music_list"] = music_list
    context.chat_data["total_page"] = len(music_list) // context.chat_data["paginator"] + 1

    context.bot.edit_message_text(
        text=f"Page: {context.chat_data['current_page']}/{context.chat_data['total_page']}",
        chat_id=update.effective_chat.id,
        message_id=query.message.message_id,
        reply_markup=music_list_keyboard())


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
    data = query.data
    index = int(data.split("_")[-1])

    download_link = ''.join([REST_URI, music_list[index]]).replace(' ', '%20')

    query.answer()
    query.edit_message_text(text=f"Download link: {download_link}")

    # context.chat_data["index"] = index
    # context.chat_data["music_list"] = music_list
    # upload_music_to_bot(update, context)


def download_audio(update, context):
    """Get download audio link from youtube link"""

    query = update.callback_query
    url = context.chat_data['url']
    logging.info(f"Getting download link for {url}")
    link = youtubedl.get_audio_url(url)

    query.edit_message_text(f"Audio download link: {link}")


@send_upload_audio_action
def download_video(update, context):
    """Get download video link from youtube link"""

    query = update.callback_query
    url = context.chat_data['url']
    logging.info(f"Getting download link for {url}")
    link = youtubedl.get_video_url(url)

    query.edit_message_text(f"Video download link: {link}")


# Corona virus data
def callback_country_select(update, context):
    """Send corona virus data of selected country"""

    query = update.callback_query
    country = query.data.split('corona_')[-1]
    corona_data = context.chat_data['corona_data']
    country_list = context.chat_data['country_list']

    context.bot.edit_message_text(text=corona_data[country],
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id,
                                  reply_markup=corona_menu_keyboard(country_list))


def update_corona_data(update, context):
    """Manually update corona virus data"""

    query = update.callback_query
    country_list = context.chat_data['country_list']

    context.bot.edit_message_text(text="Updating database ...",
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id,
                                  reply_markup=corona_menu_keyboard(country_list))

    context.bot.edit_message_text(text="Database updated successfully.",
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id,
                                  reply_markup=corona_menu_keyboard(country_list))


def start_bot(update, context):
    if mode == 'dev':
        context.bot.send_message(text="Running in dev mode",
                                 chat_id=update.effective_chat.id)
    else:
        context.bot.send_message(text="Running in production mode",
                                 chat_id=update.effective_chat.id)

    response = f"Hi, {update.effective_chat.username}. Are you a 0 or a 1 ?"
    context.bot.send_message(text=response,
                             chat_id=update.effective_chat.id,
                             reply_markup=main_menu_keyboard())


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
    """Send a random dog image"""

    query = update.callback_query
    dog_img = get_dog_img()

    context.bot.send_message(chat_id=update.effective_chat.id, text=dog_img)
    context.bot.send_message(chat_id=query.message.chat_id,
                             message_id=query.message.message_id,
                             text='Welcome to Mr Rose Bot !!! Are you a 0 or a 1 ?',
                             reply_markup=main_menu_keyboard())


def youtube_download_help(update, context):
    """Help function"""

    response = "Send a youtube link to get a downloadable link."
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=response)


def youtube_link_handle(update, context):
    """Filter youtube link"""

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


def main(*, use_proxy=True):
    logging.info("Running main func.")
    if use_proxy:
        request_kwargs = {'proxy_url': proxy}
        logging.info("Using proxy: {}".format(proxy))
    else:
        request_kwargs = {}
        logging.info("Not using proxy")
    updater = Updater(token=BOT_TOKEN, use_context=True, request_kwargs=request_kwargs)
    dispatcher = updater.dispatcher
    j_queue = updater.job_queue

    start_handler = CommandHandler('start', start_bot)
    inline_caps_handler = InlineQueryHandler(inline_caps)
    dog_handler = CallbackQueryHandler(dog, pattern="dog_image")
    help_handler = CommandHandler('help', help_bot)
    music_handler = CommandHandler('music', list_all_files)
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
    dispatcher.add_handler(CallbackQueryHandler(update_corona_data, pattern="update_corona_data"))

    dispatcher.add_handler(MessageHandler(Filters.regex('youtu.be|youtube.com'), youtube_link_handle))
    dispatcher.add_handler(CallbackQueryHandler(download_audio, pattern='download_audio'))
    dispatcher.add_handler(CallbackQueryHandler(download_video, pattern='download_video'))
    dispatcher.add_handler(CallbackQueryHandler(youtube_download_help, pattern='youtube-dl-help'))

    dispatcher.add_handler(set_timer_handler)
    dispatcher.add_handler(unknown_handler)
    dispatcher.add_handler(echo_back_handler)

    j_minute = j_queue.run_repeating(callback_welcome, interval=30, first=0)
    j_minute.enabled = False

    run(updater)


if __name__ == '__main__':

    corona_updater = bs4Virus.VirusUpdater()

    if mode == "prod":
        main(use_proxy=USE_PROXY)
        sched = BlockingScheduler()

        @sched.scheduled_job('interval', hours=1)
        def ping_bot():
            HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
            BOT_TOKEN = os.environ.get("BOT_TOKEN")
            r = requests.get(f'https://{HEROKU_APP_NAME}.herokuapp.com/{BOT_TOKEN}')

        @sched.scheduled_job('cron', year='*', month='*', day='*', hour=14, minute=18)
        def update_database():
            corona_updater.update_database()

        sched.start()

    else:
        logging.info("Getting proxy list.")
        proxies = get_proxies()
        proxy_pool = cycle(proxies)

        while 1:
            try:
                proxy = next(proxy_pool)
                main(use_proxy=USE_PROXY)
                sched = BlockingScheduler()

                @sched.scheduled_job('interval', seconds=60)
                def update_database():
                    corona_updater.update_database()

                sched.start()

            except NetworkError:
                continue
