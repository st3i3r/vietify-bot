import datetime
import configparser
import requests
import json

config = configparser.ConfigParser()
config.read('config.ini')

GEO_URI = config['geocoding']['URI']
GEO_API_KEY = config['geocoding']['API_KEY']

CURRENT_WEATHER_URI = config['weather']['CURRENT_WEATHER_URI']
WEATHER_API_KEY = config['weather']['API_KEY']
ONE_CALL_URI = config['weather']['ONE_CALL_URI']


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
    r = requests.get(GEO_URI.format(address=address, api_key=GEO_API_KEY))
    response = json.loads(r.text)

    status = response['status']
    result = response['results']

    if result:
        lat = result[0]['geometry']['location']['lat']
        long = result[0]['geometry']['location']['lat']
    else:
        lat = long = None

    return (lat, long), status


def current_weather(address):
    (lat, lon), status = get_coordinates(address)
    r = requests.get(ONE_CALL_URI.format(lat=lat, lon=lon, part='hourly', api_key=WEATHER_API_KEY))
    weather_info = json.loads(r.text)['current']

    for k, v in weather_info.items():
        print(f'{k}: {v}')

    try:
        result = [f'City: {address}',
                  f"Weather: {weather_info['weather'][0]['main']}",
                  f"Description: {weather_info['weather'][0]['description']}",
                  f"Temperature: {weather_info['temp']} °C",
                  f"Feels like: {weather_info['feels_like']} °C",
                  f"Humidity: {weather_info['humidity']}%",
                  f"Wind speed: {weather_info['wind_speed']} m/s",
                  f"Last updated: {datetime.datetime.now().strftime('%d %b %H:%M')}"]

    except KeyError:
        result = ['City not found.']

    return '\n'.join(result)


def get_weather_data(address, part='daily'):
    (lat, lon), status = get_coordinates(address)
    if status == 'OK':
        r = requests.get(ONE_CALL_URI.format(lat=lat, lon=lon, part='hourly', api_key=WEATHER_API_KEY))
        result = json.loads(r.text)
        weather_info = []
        current_time = datetime.datetime.now()
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
                                f'Last updated: {current_time.strftime("%d %b %H:%M:%S")}\n'
                                f'-----------------------------------------')

        return '\n'.join(weather_info)
    else:
        print(f'Error !!! Status code: {status}')
        return None


if __name__ == '__main__':
    current_weather('Moscow')
