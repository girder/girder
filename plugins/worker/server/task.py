import time
from celery import Celery

app = Celery('tasks', broker='pyamqp://guest@localhost//')


@app.task(name='task_sleep')
def add(x, y):
    time.sleep(300)
    return x + y
