from python:3.6

RUN apt-get update
#     && DEBIAN_FRONTEND=noninteractive apt-get install -y

RUN mkdir /usr/src/app
WORKDIR /usr/src/app
COPY ./requirements.txt .
RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED 1

COPY . .
