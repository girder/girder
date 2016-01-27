from girder.api import access
from girder.api.rest import Resource
from girder.api.describe import Description, describeRoute
from girder.plugins.worker import getCeleryApp


class Validator(Resource):
    def __init__(self, celeryApp):
        self.resourceName = 'worker_validator'
        self.route('GET', (), self.listValidators)

    @access.public
    @describeRoute(
        Description('List or search for validators.')
        .param('type', 'Find validators with this type.', required=False)
        .param('format', 'Find validators with this format.', required=False)
    )
    def listValidators(self, params):
        return getCeleryApp().send_task('girder_worker.validators', [
            params.get('type', None),
            params.get('format', None)]
        ).get()
