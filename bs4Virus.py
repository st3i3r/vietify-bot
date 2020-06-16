from bs4 import BeautifulSoup
import datetime
import time
import requests
import pandas
from lxml.html import fromstring


def check_last_update(func):
    def wrapper(*args):
        current_time = datetime.datetime.now()
        if current_time > wrapper.over_datetime or args not in wrapper.cache_data:
            print("Fetching new data from web.")
            data = func(*args)
            wrapper.cache_data[args] = data
            wrapper.last_update = current_time
            wrapper.over_datetime = wrapper.last_update + datetime.timedelta(hours=3)
            return data
        else:
            print("Using cache data.")
            return wrapper.cache_data[args]

    wrapper.cache_data = dict()
    wrapper.last_update = datetime.datetime.now()
    wrapper.over_datetime = datetime.datetime(wrapper.last_update.year,
                                              wrapper.last_update.month,
                                              wrapper.last_update.day,
                                              wrapper.last_update.hour,
                                              wrapper.last_update.minute + 1,
                                              wrapper.last_update.second,
                                              wrapper.last_update.microsecond)
    return wrapper


@check_last_update
def test(mes):
    print(mes)


class VirusUpdater:

    def __init__(self):
        self.url = 'https://www.worldometers.info/coronavirus/#countries/'

    @property
    def data(self):
        return self.fetch_data()

    @check_last_update
    def fetch_data(self):
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

        return data

    def get_by_country(self, country, *, use_cache=True):
        try:
            index = self.data.index[self.data['countries'] == country.lower()]
            data = self.data.loc[index[0]].to_string()
        except IndexError:
            data = "Country not found."

        return data

    def __str__(self):
        return self.data.to_string()


if __name__ == '__main__':
    a = VirusUpdater()
    print(a.get_by_country("vietnam"))
    time.sleep(5)
    print(a.get_by_country("vietnam"))
    time.sleep(20)
    print(a.get_by_country("russia"))
    print(a.get_by_country("russia"))
    print(a.get_by_country("russia"))
    print(a.get_by_country("russia"))
