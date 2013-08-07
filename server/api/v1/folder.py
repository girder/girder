import cherrypy

from ..rest import Resource, RestException
from models import folder as folderModel
from models.model_base import ValidationException
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

    def createFolder(self, params):
        """
        Create a new folder.
        :param parentId: The _id of the parent folder.
        :type parentId: str
        :param parentType: The type of the parent of this folder.
        :type parentType: str - 'user', 'community', or 'folder'
        :param name: The name of the folder to create.
        :param description: Folder description.
        :param public: Public read access flag.
        :type public: bool
        """
        self.requireParams(['name', 'parentId'], params)

        parentType = params.get('parentType', 'folder').lower()
        name = params['name'].strip()
        description = params.get('description', '').strip()
        public = params.get('public', None)

        if public is not None:
            public = public.lower() == 'true'

        if not name:
            raise RestException('Folder name cannot be empty.')

        user = self.getCurrentUser()

        if parentType == 'folder':
            model = self.folderModel
        elif parentType == 'user':
            model = self.userModel
        elif parentType == 'community':
            pass #TODO model = self.communityModel
        else:
            raise RestException('Set parentType to community, folder, or user.')

        parent = self.getObjectById(model, id=params['parentId'], user=user,
                                    checkAccess=True, level=AccessType.WRITE)

        try:
            folder = self.folderModel.createFolder(parent=parent, parentType=parentType,
                                                   name=name, description=description,
                                                   creator=user, public=public)
        except ValidationException as e:
            raise RestException(e.message)

        if parentType == 'user':
            folder = self.folderModel.setUserAccess(folder, user=user, level=AccessType.ADMIN)
        elif parentType == 'community':
            # TODO set appropriate top-level community folder permissions
            pass
        return self._filter(folder)

    @Resource.endpoint
    def GET(self, path, params):
        if not path:
            return self.index(params)
        else: # assume it's a folder id
            user = self.getCurrentUser()
            folder = self.getObjectById(self.folderModel, id=path[0],
                                        checkAccess=True, user=user)
            return self._filter(folder)

    @Resource.endpoint
    def POST(self, path, params):
        """
        Use this endpoint to create a new folder.
        """
        return self.createFolder(params)
