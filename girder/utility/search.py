from functools import partial

from bson.objectid import ObjectId

from girder.constants import AccessType
from girder.exceptions import GirderException, ValidationException
from girder.utility.model_importer import ModelImporter

_allowedSearchMode = {}


def getSearchModeHandler(mode):
    """
    Get the handler function for a search mode

    :param mode: A search mode identifier.
    :type mode: str
    :returns: A search mode handler function, or None.
    :rtype: function or None
    """
    return _allowedSearchMode.get(mode)


def addSearchMode(mode, handler):
    """
    Register a search mode.

    New searches made for the registered mode will call the handler function. The handler function
    must take parameters: `query`, `types`, `user`, `level`, `limit`, `offset`, and return the
    search results.

    :param mode: A search mode identifier.
    :type mode: str
    :param handler: A search mode handler function.
    :type handler: function
    """
    if _allowedSearchMode.get(mode) is not None:
        raise GirderException('A search mode %r already exists.' % mode)
    _allowedSearchMode[mode] = handler


def removeSearchMode(mode):
    """
    Remove a search mode.

    This will fail gracefully (returning `False`) if no search mode `mode` was registered.

    :param mode: A search mode identifier.
    :type mode: str
    :returns: Whether the search mode was actually removed.
    :rtype: bool
    """
    return _allowedSearchMode.pop(mode, None) is not None


def hierarchySearchPipeline(parentType, parentId, user, resultType='item', prefix=''):
    """
    Build aggregation stages that restrict a search to part of the hierarchy.

    For a folder, this walks up from each document to its ancestors, so the cost doesn't grow with
    the size of the subtree. Add the stages after the search's own match and before paging.

    :param parentType: One of 'collection', 'folder', or 'user'.
    :type parentType: str
    :param parentId: The id of the resource to search within.
    :param user: The user performing the search, for access checks.
    :param resultType: The kind of document being restricted, either 'item' or 'folder'.
    :type resultType: str
    :param prefix: Prefix for the keys of the documents being restricted.
    :type prefix: str
    :returns: A list of pipeline stages.
    :rtype: list
    """
    # Avoid circular import
    from girder.models.folder import Folder

    if parentType not in ('collection', 'folder', 'user'):
        raise ValidationException('Invalid parentType.', field='parentType')
    if resultType not in ('item', 'folder'):
        raise ValidationException('Invalid resultType.', field='resultType')
    try:
        parentId = ObjectId(parentId)
    except Exception:
        raise ValidationException('Invalid parentId.', field='parentId')

    if parentType != 'folder':
        # Documents record the collection or user at the root of their tree.
        return [{'$match': {
            prefix + 'baseParentType': parentType,
            prefix + 'baseParentId': parentId,
        }}]

    folder = Folder().load(parentId, user=user, level=AccessType.READ, exc=True)
    return [
        # Skip the walk for documents under a different root.
        {'$match': {
            prefix + 'baseParentType': folder['baseParentType'],
            prefix + 'baseParentId': folder['baseParentId'],
        }},
        # Items start at their own folder and folders at their parent, so a folder isn't its own
        # result.
        {'$graphLookup': {
            'from': Folder().name,
            'startWith': '$' + prefix + ('folderId' if resultType == 'item' else 'parentId'),
            'connectToField': '_id',
            'connectFromField': 'parentId',
            'as': '_hierarchyAncestors',
        }},
        {'$match': {'_hierarchyAncestors._id': folder['_id']}},
        {'$project': {'_hierarchyAncestors': False}},
    ]


def _commonSearchModeHandler(mode, query, types, user, level, limit, offset):
    """
    The common handler for `text` and `prefix` search modes.
    """
    # Avoid circular import
    from girder.api.v1.resource import allowedSearchTypes

    method = '%sSearch' % mode
    results = {}

    for modelName in types:
        if modelName not in allowedSearchTypes:
            continue

        if '.' in modelName:
            name, plugin = modelName.rsplit('.', 1)
            model = ModelImporter.model(name, plugin)
        else:
            model = ModelImporter.model(modelName)

        if model is not None:
            results[modelName] = [
                model.filter(d, user) for d in getattr(model, method)(
                    query=query, user=user, limit=limit, offset=offset, level=level)
            ]
    return results


# Add dynamically the default search mode
addSearchMode('text', partial(_commonSearchModeHandler, mode='text'))
addSearchMode('prefix', partial(_commonSearchModeHandler, mode='prefix'))
