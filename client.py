import configparser
import json
import os
import asyncio
import telethon
from telethon.tl.types import PeerChannel
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.functions.messages import SearchRequest
import time

#Parse Info
config = configparser.ConfigParser()
config.read("config.ini")

api_id = config['Telegram']['api_id']
api_hash = config['Telegram']['api_hash']
phone = config['Telegram']['phone']
username = config['Telegram']['username']
default_url = config['Telegram']['default_channel_url']


# Create Telegram client
client = telethon.TelegramClient(username, api_id=api_id, api_hash=api_hash)
loop = asyncio.get_event_loop()


async def main():
    await client.connect()
    print("Client started".center(30, '='))

    if not await client.is_user_authorized():
        await client.send_code_request(phone=phone)
        try:
            await client.sign_in(phone, 'Enter code: ')
        except telethon.SessionPasswordNeededError:
            await client.sign_in(password=input("Password: "))

    # Get channel
    #user_input_channel = input("Enter chanel (URL or entity): ")
    user_input_channel = ''

    if user_input_channel.isdigit():
        entity = PeerChannel(int(user_input_channel))
    elif not user_input_channel:
        entity = default_url
    else:
        entity = user_input_channel

    my_channel = await client.get_entity(entity)
    channel_name = my_channel.title

    # Configuration for download
    offset_id = 0
    downloaded_messages = []
    total_messages = 0
    total_medias = 0
    limit_messages = 100
    limit_medias = 100

    # Get channel messages
    while client.is_connected():
        print(f"Current offset id: {offset_id}")
        print(f"Total messages: {total_messages}")

        get_hisory = client(GetHistoryRequest(
                        peer=my_channel,
                        offset_id=offset_id,
                        offset_date=None,
                        add_offset=0,
                        limit=100,
                        max_id=0,
                        min_id=0,
                        hash=0))
        get_media = client.download_media(my_channel)
        tasks = get_hisory, get_media
        history, medias = await asyncio.gather(*tasks)

        if not history.messages:
            break
        else:
            messages = history.messages

        # Delete all files in medias folder
        media_dir = os.path.join("downloaded_photo", channel_name)
        if os.path.exists(media_dir):
            media_list = [f for f in os.listdir(media_dir)]
            for media in media_list:
                os.remove(os.path.join(media_dir, media))
        else:
            os.mkdir(media_dir)

        # Get photos of channel
        index = 1
        for i, mes in enumerate(messages):
            if mes.photo:
                if not mes.message:
                    photo_path = os.path.join(media_dir, f'img-{index}.jpg')
                    index += 1
                else:
                    photo_path = os.path.join(media_dir, f'{mes.message}.jpg')

                await client.download_media(mes, file=photo_path)
                total_medias += 1
                print(f"Saved photo in {photo_path}. Total photos: {total_medias}".center(50, '-'))
            else:
                # Save normal messages
                downloaded_messages.append(mes.to_dict())
                print(f"Got message. Total messages: {total_messages}".center(20, '-'))
                total_messages += 1

        offset_id = messages[-1].id

    # Print downloaded message
    for mes_from_user in messages:
        if mes_from_user.message:
            print(mes_from_user.message)


with client:
    loop.run_until_complete(main())
