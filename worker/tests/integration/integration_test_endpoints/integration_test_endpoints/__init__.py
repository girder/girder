from girder.plugin import GirderPlugin

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, Prefix

from girder_worker.app import app
from celery.exceptions import TimeoutError

from .raw import CeleryTestEndpoints
from .docker import DockerTestEndpoints


class CommonTestEndpoints(Resource):
    def __init__(self):
        super().__init__()

        # POST because get_result is not idempotent.
        self.route('POST', ('result', ), self.get_result)

    @access.token
    @describeRoute(
        Description('Utility endpoint to get an async result from a celery id')
        .param('celery_id', 'celery async ID', dataType='string'))
    def get_result(self, params):
        cid = params['celery_id']
        a1 = app.AsyncResult(cid)

        # Note: There is no reasonable way to validate a celery task
        # asyncresult id. See:
        # https://github.com/celery/celery/issues/3596#issuecomment-262102185
        # This means for ALL values of celery_id return either the
        # value or None. Note also that you will only be able to get
        # the result via this method once. All subsequent calls will
        # return None.
        try:
            return a1.get(timeout=0.2)
        except TimeoutError:
            return None


class IntegrationTestPlugin(GirderPlugin):
    DISPLAY_NAME = 'Integration Test Endpoints'

    def load(self, info):
        info['apiRoot'].integration_tests = Prefix()
        info['apiRoot'].integration_tests.common = CommonTestEndpoints()
        info['apiRoot'].integration_tests.celery = CeleryTestEndpoints()
        info['apiRoot'].integration_tests.docker = DockerTestEndpoints()
