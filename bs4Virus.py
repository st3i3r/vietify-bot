from bs4 import BeautifulSoup
import requests
import pandas


class VirusUpdater:

    def __init__(self):
        self.url = 'https://www.worldometers.info/coronavirus/#countries/'

    def __str__(self):
        return self.data.to_string()

    @property
    def data(self):
        response = requests.get(url=self.url).text
        soup = BeautifulSoup(response, 'html.parser')

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
            countries.append(data[0].text.replace("\n", "").lower())
            total_cases.append(data[1].text)
            new_cases.append(data[2].text)
            total_deaths.append(data[3].text.strip())
            new_deaths.append(data[4].text)
            total_recovered.append(data[5].text)

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

    def get_by_country(self, user_country):
        try:
            index = self.data.index[self.data['countries'] == user_country.lower()]
            data = self.data.loc[index[0]].to_string()
            response = f"==========================\n" \
                      f"{data}\n" \
                      f"rank: {str(index[0]).rjust(20)}\n"
        except IndexError:
            response = "Country not found."

        return response


if __name__ == '__main__':
    a = VirusUpdater()
    print(a.data.to_string())
    print(a.get_by_country("uSa"))
