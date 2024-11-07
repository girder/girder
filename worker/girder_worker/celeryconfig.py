import os
import configparser
import girder_worker

accept_content = ['json', 'pickle', 'yaml', 'girder_io']

broker_url = os.environ.get('GIRDER_WORKER_BROKER', None) or \
    girder_worker.config.get('celery', 'broker')

try:
    result_backend = os.environ.get('GIRDER_WORKER_BACKEND', None) or \
        girder_worker.config.get('celery', 'backend')
except configparser.NoOptionError:
    result_backend = broker_url
