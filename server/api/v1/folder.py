import cherrypy

from ..rest import Resource, RestException
from models import folder as folderModel
from constants import AccessType

class Folder(Resource):

    def initialize(self):
        self.requireModels(['folder'])

    def _filter(self, folder):
        """
        Filter a folder document for display to the user.
        """
        # TODO possibly write a folder filter with self.filterDocument
        return folder

    def index(self, params):
        return 'todo: folder index'

    @Resource.endpoint
    def GET(self, pathParam=None, **params):
        if pathParam is None:
            return self.index(params)
        else: # assume it's a folder id
            user = self.getCurrentUser()
            folder = self.getObjectById(self.folderModel, id=pathParam,
                                        checkAccess=True, user=user)
            return self._filter(folder)

    @Resource.endpoint
    def POST(self, pathParam=None, **params):
        """
        Use this endpoint to create a new folder.
        """
        raise RestException('Not implemented', 405)
