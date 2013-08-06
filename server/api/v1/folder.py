import cherrypy

from ..rest import Resource, RestException
from models import folder as folderModel

class Folder(Resource):

    def getRequiredModels(self):
        return ['folder']

    def index(self, params):
        return 'todo: folder index'

    @Resource.endpoint
    def GET(self, pathParam=None, **params):
        if pathParam is None:
            return self.index(params)
        else: # assume it's a folder id
            return self.getObjectById(self.folderModel, pathParam)

    @Resource.endpoint
    def POST(self, pathParam=None, **params):
        """
        Use this endpoint to create a new folder.
        """
        raise RestException('Not implemented', 405)
