from __future__ import unicode_literals
import youtube_dl

ytdl_audio_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'm4a',
        'preferredquality': '500',
    }],
    'outtmpl': '%(title)s.%(ext)s',
    'quiet': True
}

ytdl_video_opts = {
    'format': 'best',
    'quiet': True
}


def get_audio_url(url):
    with youtube_dl.YoutubeDL(ytdl_audio_opts) as ytdl:
        info = ytdl.extract_info(url, download=False)

    return info['url']


def get_video_url(url):
    with youtube_dl.YoutubeDL(ytdl_video_opts) as ytdl:
        info = ytdl.extract_info(url, download=False)

    return info['url']


if __name__ == "__main__":
    with youtube_dl.YoutubeDL(ytdl_audio_opts) as ytdl:
        info = ytdl.extract_info(url, download=False)
    for key, value in info.items():
        print(f"{key}: {value}")
