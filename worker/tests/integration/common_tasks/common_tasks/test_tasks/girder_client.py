from girder_worker.utils import girder_job
from girder_worker.app import app


@girder_job(title='Request Private Path')
@app.task(bind=True)
def request_private_path(self, user='admin'):
    assert hasattr(self, 'girder_client')

    # This will either work,  or throw an HttpError Exception
    self.girder_client.resourceLookup('/user/%s/Private' % user)
