import json
from girder import events
from girder.api import access, rest
from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.folder import Folder
from girder.models.item import Item


def _validateFolder(event):
    doc = event.info

    if 'isVirtual' in doc and not isinstance(doc['isVirtual'], bool):
        raise ValidationException('The isVirtual field must be boolean.', field='isVirtual')

    if doc.get('isVirtual'):
        # Make sure it doesn't have child items
        if list(Folder().childItems(doc, limit=1)):
            raise ValidationException(
                'Virtual folders may not contain child items.', field='isVirtual')

    if 'virtualItemsQuery' in doc:
        try:
            json.loads(doc['virtaulItemsQuery'])
        except (TypeError, ValueError):
            raise ValidationException(
                'The virtual items query must be valid JSON.', field='virtualItemsQuery')

    if 'virtualItemsSort' in doc:
        try:
            json.loads(doc['virtualItemsSort'])
        except (TypeError, ValueError):
            raise ValidationException(
                'The virtual items sort must be valid JSON.', field='virtualItemsSort')


def _validateItem(event):
    parent = Folder().load(event.info['folderId'], force=True)
    if parent.get('isVirtual'):
        raise ValidationException(
            'You may not place items under a virtual folder.', field='folderId')


@access.public
@rest.boundHandler
def _virtualChildItems(self, event):
    params = event.info['params']

    if 'folderId' not in params:
        return  # This is not a child listing request

    user = self.getCurrentUser()
    folder = Folder().load(params['folderId'], user=user, level=AccessType.READ)

    if not folder.get('isVirtual') or 'virtualItemsQuery' not in folder:
        return  # Parent is not a virtual folder, proceed as normal

    limit, offset, sort = self.getPagingParameters(params, defaultSortField='name')
    q = json.loads(folder['virtualItemsQuery'])

    if 'virtualItemsSort' in folder:
        sort = json.loads(folder['virtualItemsSort'])

    item = Item()
    # These items may reside in folders that the user cannot read, so we must filter
    items = item.filterResultsByPermission(
        item.find(q, sort=sort), user, level=AccessType.READ, limit=limit, offset=offset)
    event.preventDefault().addResponse([item.filter(i, user) for i in items])


def load(info):
    events.bind('model.folder.validate', info['name'], _validateFolder)
    events.bind('model.item.validate', info['name'], _validateItem)
    events.bind('rest.get.item.before', info['name'], _virtualChildItems)
    Folder().exposeFields(level=AccessType.READ, fields={'isVirtual'})


# TODO augment folder update & creation endpoints to accept virtual-related params
