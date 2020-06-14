from bs4 import BeautifulSoup
import requests
import pandas
from lxml.html import fromstring


class VirusUpdater:

    def __init__(self):
        self.url = 'https://www.worldometers.info/coronavirus/#countries/'

    @property
    def data(self):
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

    def get_by_country(self, country):
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
    a.test()
