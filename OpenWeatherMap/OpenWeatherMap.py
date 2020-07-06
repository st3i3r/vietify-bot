import datetime
import configparser
import requests
import json
import os
from collections import namedtuple


__all__ = ['current_weather', 'get_weather_data']

mode = os.getenv('MODE')

if mode == 'dev':
    config = configparser.ConfigParser()
    config.read('config.ini')

    GEO_URI = config['geocoding']['URI']
    GEO_API_KEY = config['geocoding']['API_KEY']

    WEATHER_API_KEY = config['weather']['API_KEY']
    ONE_CALL_URI = config['weather']['ONE_CALL_URI']

elif mode == 'prod':
    GEO_URI = 'https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}'
    GEO_API_KEY = os.environ.get('GEO_API_KEY')
    
    ONE_CALL_URI = 'https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&exclude={part}&appid={api_key}&units=metric'
    WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY')


def cache(fn):
    def wrapper(*args, **kwargs):
        cache_key = args
        if cache_key not in wrapper.cache_data:
            print('Not using cache coordinates')
            result = fn(*args, **kwargs)
            wrapper.cache_data[cache_key] = result
        return wrapper.cache_data[cache_key]

    wrapper.cache_data = dict()
    return wrapper


@cache
def get_coordinates(address):
    """Convert address to latitude and longtitude coordinates."""

    GeoInfo = namedtuple('GeoInfo', 'lat long status')

    r = requests.get(GEO_URI.format(address=address, api_key=GEO_API_KEY))
    response = json.loads(r.text)

    status = response['status']
    result = response['results']

    if result:
        lat = result[0]['geometry']['location']['lat']
        long = result[0]['geometry']['location']['lat']
    else:
        lat = long = None

    return GeoInfo(lat, long, status)


def current_weather(address):
    """Get current weather."""

    lat, lon, status = get_coordinates(address)
    r = requests.get(ONE_CALL_URI.format(lat=lat, lon=lon, part='hourly', api_key=WEATHER_API_KEY))
    weather_info = json.loads(r.text)['current']

    try:
        result = [f'City: {address}',
                  f"Weather: {weather_info['weather'][0]['main']}",
                  f"Description: {weather_info['weather'][0]['description']}",
                  f"Temperature: {weather_info['temp']} °C",
                  f"Feels like: {weather_info['feels_like']} °C",
                  f"Humidity: {weather_info['humidity']}%",
                  f"Wind speed: {weather_info['wind_speed']} m/s",
                  f"Last updated: {(datetime.datetime.utcnow() + datetime.timedelta(hours=3)).strftime('%d %b %H:%M')}"]

    except KeyError:
        result = ['City not found.']

    return '\n'.join(result)


def get_weather_data(address, part='daily'):
    """Get weather forecast for next days"""

    lat, lon, status = get_coordinates(address)
    if status == 'OK':
        r = requests.get(ONE_CALL_URI.format(lat=lat, lon=lon, part='hourly', api_key=WEATHER_API_KEY))
        result = json.loads(r.text)

        current_time = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
        weather_info = [f'City: {address}\n'
                        f'Last updated: {current_time.strftime("%d %b %H:%M:%S")}\n']
        for i in range(4):
            day = (current_time + datetime.timedelta(days=i)).strftime('%d %b %Y')
            weather_info.append(f'{day}\n'
                                f'Weather: {result[part][i]["weather"][0]["main"]}\n'
                                f'Day: {result[part][i]["temp"]["day"]} - '
                                f'feels like: {result[part][i]["feels_like"]["day"]}\n'
                                f'Eve: {result[part][i]["temp"]["eve"]} - '
                                f'feels like: {result[part][i]["feels_like"]["eve"]}\n'
                                f'Night: {result[part][i]["temp"]["night"]} - '
                                f'feels like: {result[part][i]["feels_like"]["night"]}\n'
                                f'-----------------------------------------')

        return '\n'.join(weather_info)
    else:
        return f'Error !!! Status code: {status}'


if __name__ == '__main__':
    current_weather('Moscow')
