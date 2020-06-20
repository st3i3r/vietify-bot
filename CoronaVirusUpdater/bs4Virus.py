from bs4 import BeautifulSoup
import datetime
import time
import requests
import pandas
from functools import wraps
from apscheduler.schedulers.blocking import BlockingScheduler

TIME_ZONE = {'Vietnam': 8,
             'Moscow': 3}

sched = BlockingScheduler()


def check_last_update(func):
    @wraps(func)
    def wrapper(*args, use_cache):
        current_time = datetime.datetime.utcnow() + datetime.timedelta(hours=TIME_ZONE['Moscow'])
        if not use_cache or current_time > wrapper.over_datetime or not wrapper.cache_data:
            data = func(*args, use_cache)
            wrapper.cache_data['latest-data'] = data

            wrapper.last_update = current_time
            wrapper.over_datetime = wrapper.last_update + datetime.timedelta(hours=5)

            return data
        else:
            return wrapper.cache_data['latest-data']

    wrapper.cache_data = dict()
    wrapper.last_update = datetime.datetime.utcnow() + datetime.timedelta(hours=TIME_ZONE['Moscow'])
    wrapper.over_datetime = wrapper.last_update + datetime.timedelta(hours=5)

    return wrapper


class VirusUpdater:

    def __init__(self):
        self.url = 'https://www.worldometers.info/coronavirus/#countries/'
        self.use_cache = True
        self.data = None
        self.last_updated = None

    def update_database(self):
        response = requests.get(url=self.url)
        soup = BeautifulSoup(response.content, 'html.parser')

        ranks = []
        countries = []
        total_cases = []
        new_cases = []
        total_deaths = []
        new_deaths = []
        total_recovered = []
        COUNT = 200

        tbody = soup.find('tbody')
        rows = tbody.find_all('tr')

        for i in range(COUNT):
            data = rows[i].find_all('td')
            ranks.append(data[0].text)
            countries.append(data[1].text.replace("\n", "").lower())
            total_cases.append(data[2].text)
            new_cases.append(data[3].text)
            total_deaths.append(data[4].text.strip())
            new_deaths.append(data[5].text)
            total_recovered.append(data[6].text)

        data = pandas.DataFrame({
            'ranks': ranks,
            'countries': countries,
            'total_cases': total_cases,
            'new_cases': new_cases,
            'total_deaths': total_deaths,
            'new_deaths': new_deaths,
            'total_recovered': total_recovered,
        })

        data.replace('', '-', inplace=True)

        self.data = data
        self.last_updated = datetime.datetime.utcnow() + datetime.timedelta(hours=TIME_ZONE['Moscow'])

    def get_by_country(self, country):
        try:
            if self.data is None:
                self.update_database()

            index = self.data.index[self.data['countries'] == country.lower()]
            data = self.data.loc[index[0]].to_string()
            data += f"\nLast updated: {self.last_updated.strftime('%d %b %H:%M %Z')}"
        except IndexError:
            data = "Country not found."

        return data

    def __str__(self):
        return self.data.to_string()


if __name__ == '__main__':
    a = VirusUpdater()
    print(a.get_by_country("Vietnam", use_cache=True))
    time.sleep(10)
    print(a.get_by_country("Vietnam", use_cache=False))
