import inspect
from functools import partial

from bson.objectid import ObjectId

from girder.constants import AccessType
from girder.exceptions import GirderException, ValidationException
from girder.utility.model_importer import ModelImporter

_allowedSearchMode = {}

# Most results a restricted search reads from a handler that doesn't restrict its own query.
FALLBACK_SEARCH_READ_LIMIT = 1000
_FALLBACK_SEARCH_BATCH_SIZE = 100


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

    A handler can restrict its own query to part of the hierarchy by accepting a
    `hierarchyPipeline` parameter; see :func:`runSearch`.

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


def _handlerTakesHierarchyPipeline(handler):
    """Whether a search mode handler names a `hierarchyPipeline` parameter."""
    try:
        param = inspect.signature(handler).parameters.get('hierarchyPipeline')
    except (TypeError, ValueError):
        return False
    return param is not None and param.kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)


def _keepInHierarchy(docs, resultType, buildPipeline):
    """Keep the documents inside the restricted location, in order."""
    withIds = []
    for doc in docs:
        try:
            withIds.append((doc, ObjectId(doc['_id'])))
        except Exception:
            pass
    if not withIds:
        return []
    inside = {doc['_id'] for doc in ModelImporter.model(resultType).collection.aggregate(
        [{'$match': {'_id': {'$in': [docId for _, docId in withIds]}}}]
        + buildPipeline(resultType=resultType)
        + [{'$project': {'_id': True}}])}
    return [doc for doc, docId in withIds if docId in inside]


def _restrictSearchResults(handler, query, types, user, level, limit, offset, buildPipeline):
    """
    Restrict the results of a handler that doesn't restrict its own query, by reading them in
    batches. Stops after FALLBACK_SEARCH_READ_LIMIT results, so results may be incomplete.
    """
    results = {}
    for resultType in types:
        if resultType not in ('folder', 'item'):
            continue
        kept = []
        seen = set()
        read = 0
        while read < FALLBACK_SEARCH_READ_LIMIT:
            batchSize = min(_FALLBACK_SEARCH_BATCH_SIZE, FALLBACK_SEARCH_READ_LIMIT - read)
            batch = handler(
                query=query, types=[resultType], user=user, level=level, limit=batchSize,
                offset=read)
            batch = batch.get(resultType, []) if isinstance(batch, dict) else []
            returned = len(batch)
            read += returned
            batch = [doc for doc in batch if doc.get('_id') not in seen]
            seen.update(doc.get('_id') for doc in batch)
            kept += _keepInHierarchy(batch, resultType, buildPipeline)
            # No new results means the handler is ignoring the offset.
            if (limit and len(kept) >= offset + limit) or returned < batchSize or not batch:
                break
        results[resultType] = kept[offset:offset + limit if limit else None]
    return results


def runSearch(handler, query, types, user, level, limit, offset, parentType=None,
              parentId=None):
    """
    Run a search, optionally restricted to part of the hierarchy.

    A restricted search returns only folders and items. Handlers that accept a `hierarchyPipeline`
    parameter get a function that builds the restriction's stages (see
    :func:`hierarchySearchPipeline`) to add to their own queries. Other handlers' results are
    restricted afterwards.

    :param handler: A search mode handler function.
    :type handler: function
    :param parentType: One of 'collection', 'folder', or 'user', or None to search everywhere.
    :type parentType: str or None
    :param parentId: The id of the resource to search within.
    :returns: The search results, keyed by type.
    :rtype: dict
    """
    if parentType is None:
        return handler(
            query=query, types=types, user=user, level=level, limit=limit, offset=offset)

    buildPipeline = partial(hierarchySearchPipeline, parentType, parentId, user)
    # Validate the location and check access, even if no types can be restricted.
    buildPipeline()

    if _handlerTakesHierarchyPipeline(handler):
        results = handler(
            query=query, types=types, user=user, level=level, limit=limit, offset=offset,
            hierarchyPipeline=buildPipeline)
        if not isinstance(results, dict):
            results = {}
        # Check anyway, in case the handler ignored the pipeline.
        results = {
            resultType: _keepInHierarchy(results.get(resultType, []), resultType, buildPipeline)
            for resultType in types if resultType in ('folder', 'item')}
    else:
        results = _restrictSearchResults(
            handler, query, types, user, level, limit, offset, buildPipeline)

    # Other types can't be inside the hierarchy.
    for resultType in types:
        results.setdefault(resultType, [])
    return results


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
