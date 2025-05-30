import os

accept_content = ['json', 'pickle', 'yaml', 'girder_io']

broker_url = os.environ.get(
    'GIRDER_WORKER_BROKER', 'amqp://guest:guest@localhost/')

result_backend = os.environ.get(
    'GIRDER_WORKER_BACKEND', 'rpc://guest:guest@localhost/')

task_always_eager = os.environ.get(
    'GIRDER_WORKER_TASK_ALWAYS_EAGER', 'false').lower() == 'true'
