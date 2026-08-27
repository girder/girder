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

    Handlers should also accept `**kwargs`, as searches may pass additional optional parameters.
    Currently a search that is restricted to a location in the data hierarchy also passes
    `parentType` and `parentId`; a handler that does not accept them will only be called for
    unrestricted searches.

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


def _hierarchySearchFilters(parentType, parentId, user):
    """
    Build the query filters that restrict a search to the subtree rooted at a point in the data
    hierarchy.

    :param parentType: One of 'collection', 'folder', or 'user'.
    :type parentType: str
    :param parentId: The id of the resource to search within.
    :param user: The user performing the search, for access checks.
    :returns: A mapping of model name to a filters dict.
    :rtype: dict
    """
    # Avoid circular import
    from girder.models.folder import Folder

    try:
        parentId = ObjectId(parentId)
    except Exception:
        raise ValidationException('Invalid parentId.', field='parentId')

    if parentType == 'folder':
        folder = Folder().load(parentId, user=user, level=AccessType.READ, exc=True)
        folderIds = list(Folder().subtreeFolderIds(folder))
        return {
            # The folder being searched from is the container, not a result.
            'folder': {'_id': {'$in': [
                folderId for folderId in folderIds if folderId != folder['_id']]}},
            'item': {'folderId': {'$in': folderIds}},
        }

    filters = {'baseParentType': parentType, 'baseParentId': parentId}
    return {'folder': dict(filters), 'item': dict(filters)}


def _commonSearchModeHandler(mode, query, types, user, level, limit, offset,
                             parentType=None, parentId=None):
    """
    The common handler for `text` and `prefix` search modes.
    """
    # Avoid circular import
    from girder.api.v1.resource import allowedSearchTypes

    method = '%sSearch' % mode
    results = {}

    hierarchyFilters = None
    if parentType is not None:
        hierarchyFilters = _hierarchySearchFilters(parentType, parentId, user)

    for modelName in types:
        if modelName not in allowedSearchTypes:
            continue

        filters = None
        if hierarchyFilters is not None:
            if modelName not in hierarchyFilters:
                continue
            filters = hierarchyFilters[modelName]

        if '.' in modelName:
            name, plugin = modelName.rsplit('.', 1)
            model = ModelImporter.model(name, plugin)
        else:
            model = ModelImporter.model(modelName)

        if model is not None:
            results[modelName] = [
                model.filter(d, user) for d in getattr(model, method)(
                    query=query, user=user, limit=limit, offset=offset, level=level,
                    filters=filters)
            ]
    return results


# Add dynamically the default search mode
addSearchMode('text', partial(_commonSearchModeHandler, mode='text'))
addSearchMode('prefix', partial(_commonSearchModeHandler, mode='prefix'))
