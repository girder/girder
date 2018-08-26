import pytest
from bson.objectid import ObjectId
from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.folder import Folder

BAD_ID = ObjectId()


@pytest.mark.parametrize('model,acl', [
    ('user', {'users': [{'id': BAD_ID, 'level': AccessType.READ}]}),
    ('group', {'groups': [{'id': BAD_ID, 'level': AccessType.READ}]})
])
def testSetInvalidAclRaisesException(user, acl, model):
    folder = next(Folder().childFolders(user, 'user', user))

    with pytest.raises(ValidationException, match='No such %s: %s$' % (model, BAD_ID)):
        Folder().setAccessList(folder, acl, user=user)
