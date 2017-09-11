web: ./manage.py runserver
load_realtime: ./manage.py load_realtime
worker: celery worker -P gevent -A kirin.tasks.celery
scheduler: celery beat -A kirin.tasks.celery

