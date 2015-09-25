FROM python:2.7-onbuild

VOLUME /usr/src/config
ENV KIRIN_CONFIG_FILE /usr/src/config/settings.py
RUN pip install uWSGI
RUN apt-get update && apt-get install -y protobuf-compiler
WORKDIR /usr/src/app

RUN python setup.py build_pbf

CMD python ./manage.py db upgrade; uwsgi --http :9090 --master --processes 2 -w kirin:app

