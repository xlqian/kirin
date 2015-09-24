FROM python:2.7-onbuild

VOLUME /usr/src/config
ENV KIRIN_CONFIG_FILE /usr/src/config/settings.py
RUN pip install uWSGI
WORKDIR /usr/src/app

CMD python ./manage.py db upgrade; uwsgi --http :9090 --master --processes 2 -w kirin:app

