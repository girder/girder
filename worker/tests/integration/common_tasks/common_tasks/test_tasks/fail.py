from girder_worker.utils import girder_job
from girder_worker.app import app
import time


@girder_job(title='Fail After')
@app.task
def fail_after(seconds=0.5, **kwargs):
    time.sleep(seconds)
    raise Exception('Intentionally failed after %s seconds' % seconds)
