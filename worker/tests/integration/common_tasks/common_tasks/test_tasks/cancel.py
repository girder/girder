import time

from girder_worker.utils import girder_job
from girder_worker.app import app


@girder_job(title='Cancelable Job')
@app.task(bind=True)
def cancelable(task, sleep_interval=0.5):
    count = 0
    while not task.canceled and count < 10:
        time.sleep(sleep_interval)
        count += 1
