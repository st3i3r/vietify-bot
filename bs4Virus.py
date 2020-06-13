from bs4 import BeautifulSoup
import requests
import pandas
from lxml.html import fromstring


class VirusUpdater:

    def __init__(self):
        self.url = 'https://www.worldometers.info/coronavirus/#countries/'

    def test(self):
        response = requests.get(url=self.url)
        parser = fromstring(response.text)
        for i in parser.xpath("//tbody/tr"):
            rank = i[1]
            #country = i[1].text() or '-'

            print(rank)

    @property
    def data(self):
        response = requests.get(url=self.url)
        soup = BeautifulSoup(response.content, 'html.parser')


        countries = []
        total_cases = []
        new_cases = []
        total_deaths = []
        new_deaths = []
        total_recovered = []
        COUNT = 150

        tbody = soup.find('tbody')
        rows = tbody.find_all('tr')

        for i in range(COUNT):
            data = rows[i].find_all('td')
            countries.append(data[1].text.replace("\n", "").lower())
            total_cases.append(data[2].text)
            new_cases.append(data[3].text)
            total_deaths.append(data[4].text.strip())
            new_deaths.append(data[5].text)
            total_recovered.append(data[6].text)

        data = pandas.DataFrame({
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
            response = f"============================\n" \
                       f"{data}\n" \
                       f"rank:{str(index[0]-7).rjust(20)}\n"
        except IndexError:
            response = "Country not found."

        return response

    def __str__(self):
        return self.data.to_string()


if __name__ == '__main__':
    a = VirusUpdater()
    print(a.get_by_country('russia'))
