import os

from celery import Celery
from django.conf import settings
from celery.schedules import crontab
from honeybadger.contrib import CeleryHoneybadger

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('backend')
app.conf.update(
  HONEYBADGER_API_KEY=settings.HONEYBADGER['API_KEY'],
  HONEYBADGER_ENVIRONMENT= 'production',
  broker_connection_retry_on_startup=True,
)
CeleryHoneybadger(app, report_exceptions=True)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.broker_transport_options = {
    'priority_steps': list(range(10)),
    'sep': ':',
    'queue_order_strategy': 'priority',
    'task_queues': {
        'aso_app.tasks.country_rank': {
            'priority': 6,
        },
        'aso_app.tasks.google_country_rank': {
            'priority': 6,
        },
        'aso_app.tasks.apple_country_rank': {
            'priority': 6,
        },
        'home.tasks.check_removed_apps': {
            'priority': 4,
        }
    }
}

app.conf.beat_schedule = {
    'add-daily-at-midnight': {
        'task': 'home.tasks.daily_task',
        'schedule': crontab(hour=0, minute=0),
    },
    'add-daily-at-2-pm': {
        'task': 'aso_app.tasks.country_rank',
        'schedule': crontab(hour=14, minute=0),
    },
    'add-daily-at-9-pm': {
        'task': 'home.tasks.check_removed_apps',
        'schedule': crontab(hour=21, minute=0),
    },
    'add-daily-at-10-pm': {
        'task': 'home.tasks.rebuild_index',
        'schedule': crontab(hour=22, minute=0),
    },
    'add-mf-at-2-pm': {
        'task': 'aso_app.tasks.google_country_rank',
        'schedule': crontab(hour=14, minute=0, day_of_week='mon,fri'),
    },
    'add-w-at-2-pm': {
        'task': 'aso_app.tasks.apple_country_rank',
        'schedule': crontab(hour=14, minute=0, day_of_week='wed'),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')