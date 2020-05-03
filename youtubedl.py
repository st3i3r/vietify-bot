from pytube import YouTube
import youtube_dl
import re

URL = "https://www.youtube.com/watch?v=3BnqYYNmjDk"

ytdl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'm4a',
        'preferredquality': '500',
    }],
    'outtmpl': '%(title)s.%(ext)s',
    'quiet': False
}

if __name__ == "__main__":
    with youtube_dl.YoutubeDL(ytdl_opts) as ytdl:
        info = ytdl.extract_info(URL, download=False)
        url = info["url"]
        print(url)
