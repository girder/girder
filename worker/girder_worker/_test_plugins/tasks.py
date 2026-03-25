from girder_worker.app import app
from girder_worker.utils import types
from girder_worker.utils.decorators import argument


def not_a_task():
    pass


@argument('n', types.Integer)
def function_task(n):
    return n


@app.task
@argument('n', types.Integer)
def celery_task(n):
    return n
