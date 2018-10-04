web: KIRIN_LOG_FORMATTER='json' KIRIN_CONFIG_FILE=dev_settings.py KIRIN_USE_GEVENT=true ./manage.py runserver -p 54746
load_realtime: KIRIN_LOG_FORMATTER='json' KIRIN_CONFIG_FILE=dev_settings.py KIRIN_USE_GEVENT=true ./manage.py load_realtime
worker: KIRIN_LOG_FORMATTER='json' KIRIN_CONFIG_FILE=dev_settings.py celery worker -A kirin.tasks.celery -c 3
scheduler: KIRIN_LOG_FORMATTER='json' KIRIN_CONFIG_FILE=dev_settings.py celery beat -A kirin.tasks.celery
