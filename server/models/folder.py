import datetime

from .model_base import AccessControlledModel

class Folder(AccessControlledModel):

    def initialize(self):
        self.name = 'folder'
        self.setIndexedFields(['parentId'])

    def createFolder(self, parent, name, description='', parentType='folder', public=None,
                     creator=None):
        """
        Create a new folder under the given parent.
        :param parent: The parent document. Should be a folder, user, or community.
        :type parent: dict
        :param name: The name of the folder.
        :type name: str
        :param description: Description for the folder.
        :type description: str
        :param parentType: What type the parent is: ('folder' | 'user' | 'community')
        :type parentType: str
        :param public: Public read access flag.
        :type public: bool or None to inherit from parent
        :param creator: User document representing the creator of this folder.
        :type creator: dict
        :returns: The folder document that was created.
        """
        assert parent.has_key('_id')
        assert public is None or type(public) is bool

        # TODO validate that no sibling has the requested name

        now = datetime.datetime.now()

        # If this is a subfolder, default permissions are inherited from the parent folder
        if parentType == 'folder' and parent.has_key('access'):
            access = parent['access']
        else: # Otherwise use an empty set of permissions; caller will handle setting them
            access = {
                'groups' : [],
                'users' : []
            }

        if public is None:
            # This means we should inherit permissions from parent or default to private
            public = parent.get('public', False)

        if creator is None:
            creatorId = None
        else:
            creatorId = creator.get('_id', None)

        return self.save({
            'name' : name,
            'description' : description,
            'parentCollection' : parentType,
            'parentId' : parent['_id'],
            'public' : public,
            'access' : access,
            'creatorId' : creatorId,
            'created' : now,
            'updated' : now,
            'size' : 0
            })
