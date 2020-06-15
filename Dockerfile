from python:3.8

RUN apt-get update
RUN pip install --upgrade pip

RUN mkdir /app
ADD . /app
WORKDIR /app

RUN pip install -r requirements.txt

CMD ["python", "/app/bot.py"]

