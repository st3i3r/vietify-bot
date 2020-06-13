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
    'format': 'bestvideo/best',
    'outtmpl': '/tmp/%(title)s.%(ext)s',
    'quiet': True
}


def download_audio(url):
    with youtube_dl.YoutubeDL(ytdl_audio_opts) as ytdl:
        info = ytdl.extract_info(url, download=True)

    return ".".join([info['title'], 'm4a'])


def download_video(url):
    with youtube_dl.YoutubeDL(ytdl_video_opts) as ytdl:
        info = ytdl.extract_info(url, download=True)

    return ".".join([info['title'], "mp4"])


if __name__ == "__main__":
    download_video("https://www.youtube.com/watch?v=wJnBTPUQS5A")
