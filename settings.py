#!/usr/bin/python
"""Celery Setting."""
from os import getenv

BROKER_SERVER = getenv('BROKER_SERVER', '127.0.0.1')
BROKER_PORT = getenv('BROKER_PORT', 5672)
BROKER_VHOST = getenv('BROKER_VHOST', '/')
BROKER_USER = getenv('BROKER_USER', 'guest')
BROKER_PASS = getenv('BROKER_PASS', 'guest')
BROKER_TRANSPORT = getenv('BROKER_TRANSPORT', 'amqp')
BROKER_URL = '{transport}://{user}:{password}@{server}:{port}/{vhost}'.format(
    transport=BROKER_TRANSPORT,
    user=BROKER_USER,
    password=BROKER_PASS,
    server=BROKER_SERVER,
    port=BROKER_PORT,
    vhost=BROKER_VHOST
)
CELERY_RESULT_BACKEND = 'rpc://'

CELERYD_STATE_DB = 'celery_worker_state'

CELERY_DISABLE_RATE_LIMITS = True

# Only add pickle to this list if your broker is secured
# from unwanted access (see userguide/security.html)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

CELERY_IGNORE_RESULT = False
