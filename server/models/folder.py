import datetime

from . import AccessControlledModel

class Folder(AccessControlledModel):

    def initialize(self):
        self.name = 'folder'
        self.setIndexedFields(['parentId'])

    def createFolder(self, parent, name, description='', parentType='folder', public=False,
                     creator=None):
        """
        Create a new folder under the given parent. Validation should be done by the caller,
        including ensuring no siblings with duplicate names exist.
        @param parent The parent document. Should be a folder, user, or community.
        @param name The name of the folder.
        @param [description=''] Description for the folder.
        @param [parentType='folder'] What type the parent is: ('folder' | 'user' | 'community')
        @param [public=False] Public read access flag.
        @param [creator=None] User document representing the creator of this folder.
        @return The folder document that was created.
        """
        assert parent.has_key('_id')
        assert type(public) is bool

        now = datetime.datetime.now()

        # If this is a subfolder, default permissions are inherited from the parent folder
        if parentType == 'folder' and parent.has_key('access'):
            access = parent['access']
        else: # Otherwise use an empty set of permissions; caller will handle setting them
            access = {
                'groups' : [],
                'users' : []
            }

        if creator is None or not creator.has_key('_id'):
            creatorId = None
        else:
            creatorId = creator['_id']

        return self.save({
            'name' : name,
            'description' : description,
            'parentCollection' : parentType,
            'parentId' : parent['_id'],
            'folders' : [],
            'items' : [],
            'public' : public,
            'access' : access,
            'creatorId' : creatorId,
            'created' : now,
            'updated' : now,
            'size' : 0
            })
