"""
Report how assetstore storage is used by users, collections, folders, items, and files.

Building the report requires a pass over all of the file records in scope,
which can take tens of seconds on a large system, so the result of that pass is
cached for a short time.  Drilling down into a user, collection, or folder uses
the cached folder totals; the items in a folder and the files in an item are
queried when they are requested.
"""
import collections
import concurrent.futures
import datetime
import heapq
import threading
import time

from girder.exceptions import NoAssetstoreAdapter, ValidationException
from girder.models.assetstore import Assetstore
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.user import User
from girder.utility import assetstore_utilities
from girder.utility import path as path_util
from girder.utility.model_importer import ModelImporter

SOURCES = ('all', 'uploaded', 'imported')
ROOT_TYPES = ('user', 'collection')
NODE_TYPES = ('user', 'collection', 'folder', 'item')

CACHE_SECONDS = 600
CACHE_ENTRIES = 8
BATCH_SIZE = 50000
# When an assetstore has more files than this, items are joined to their
# folders in the database rather than by looking up each item.
LARGE_ASSETSTORE_FILES = 100000
MAX_FOLDER_DEPTH = 1000

_cache = collections.OrderedDict()
_cacheLock = threading.Lock()
_computeLocks = {}

_FILE_FIELDS = {'name': 1, 'size': 1, 'itemId': 1, 'attachedToType': 1,
                'attachedToId': 1, 'assetstoreId': 1, 'imported': 1}


def _zero():
    return [0, 0]


def _add(total, size, count):
    total[0] += size
    total[1] += count


def _chunks(values, size=BATCH_SIZE):
    values = list(values)
    for start in range(0, len(values), size):
        yield values[start:start + size]


def _attachedType(value):
    """
    Files attached to core resources record the resource type as a string.
    Plugin resources use a list, and are reported together as other resources.
    """
    return value if isinstance(value, str) else None


class _Filters:
    """
    The options that select which files are counted.

    :param assetstore: the assetstore to report on, or None for all
        assetstores.
    :param attached: if True, include files attached to resources other than
        items, such as thumbnails.  Attached files are counted as part of the
        resource they are attached to.
    :param dedup: if True, count stored data shared by several files once.
        The oldest file sharing the data is credited with it.
    :param source: 'all', 'uploaded', or 'imported'.
    """

    def __init__(self, assetstore=None, attached=True, dedup=False, source='all'):
        if source not in SOURCES:
            raise ValidationException('Source must be one of %s.' % ', '.join(SOURCES), 'source')
        self.assetstore = assetstore
        self.attached = bool(attached)
        self.dedup = bool(dedup)
        self.source = source
        if assetstore is not None:
            self.assetstores = [assetstore]
        else:
            self.assetstores = list(Assetstore().find({}, fields=['type'], sort=[('_id', 1)]))
        self.assetstoreIds = [a['_id'] for a in self.assetstores]

    @property
    def key(self):
        return (self.assetstore['_id'] if self.assetstore else None,
                self.attached, self.dedup, self.source)

    def match(self):
        """
        Get a query matching the files in scope.
        """
        query = {'assetstoreId': {'$in': self.assetstoreIds}}
        if self.source == 'uploaded':
            query['imported'] = {'$ne': True}
        elif self.source == 'imported':
            query['imported'] = True
        if not self.attached:
            query['attachedToId'] = None
        return query


class _Summary:
    """
    Storage totals for every user, collection, and folder, computed from a
    pass over the files in scope.
    """

    def __init__(self, filters):
        start = time.time()
        self.filters = filters
        # (type, id) -> [size, count], including attached files
        self.rootTotals = collections.defaultdict(_zero)
        # (type, id) -> [size, count] of files attached to the root itself
        self.rootAttached = collections.defaultdict(_zero)
        # folder id -> [size, count] of everything under the folder
        self.folderTotals = collections.defaultdict(_zero)
        # folder id -> [size, count] of files attached to the folder itself
        self.folderAttached = collections.defaultdict(_zero)
        # (parent type, parent id) -> list of child folder ids with data
        self.folderChildren = collections.defaultdict(list)
        # (type, id) -> list of (size, file id) of files attached to a user,
        # collection, folder, or item
        self.attachedFiles = collections.defaultdict(list)
        # Files whose item, folder, or root no longer exists
        self.orphaned = _zero()
        # Files attached to resources other than users, collections, folders,
        # and items
        self.otherAttached = _zero()
        # Ids of files not counted because their stored data is credited to
        # another file
        self.duplicates = set()
        self._compute()
        self.computed = datetime.datetime.now(datetime.timezone.utc)
        self.elapsed = time.time() - start
        self.expires = time.time() + CACHE_SECONDS

    def _itemFolders(self, itemIds):
        """
        Get the folder of each item.

        :param itemIds: a collection of item ids.
        :returns: a dictionary of item id to folder id for items that exist.
        """
        result = {}
        for chunk in _chunks(itemIds):
            for doc in Item().collection.find({'_id': {'$in': chunk}}, {'folderId': 1}):
                result[doc['_id']] = doc.get('folderId')
        return result

    def _addItemFiles(self, itemTotals, folderDirect, orphaned, sign=1):
        """
        Credit per-item totals to the items' folders.

        :param itemTotals: a dictionary of item id to [size, count].
        :param folderDirect: a dictionary of folder id to [size, count] to add
            to.
        :param orphaned: a [size, count] list to add files of missing items
            to.
        :param sign: 1 to add, -1 to subtract.
        """
        itemFolder = self._itemFolders(itemTotals)
        for itemId, (size, count) in itemTotals.items():
            folderId = itemFolder.get(itemId)
            target = orphaned if folderId is None else folderDirect[folderId]
            _add(target, sign * size, sign * count)

    def _itemFileTotals(self, match):
        """
        Total the files that belong to items, including files attached to
        items, by the items' folders.

        :returns: a dictionary of folder id to [size, count], and the
            [size, count] of files whose item no longer exists.
        """
        folderDirect = collections.defaultdict(_zero)
        orphaned = _zero()
        query = dict(match)
        if self.filters.attached:
            query['$or'] = [{'itemId': {'$ne': None}}, {'attachedToType': 'item'}]
            owner = {'$ifNull': ['$itemId', '$attachedToId']}
        else:
            query['itemId'] = {'$ne': None}
            owner = '$itemId'
        pipeline = [
            {'$match': query},
            {'$group': {'_id': owner, 'size': {'$sum': '$size'}, 'n': {'$sum': 1}}},
        ]
        fileCount = File().collection.count_documents(
            {'assetstoreId': {'$in': self.filters.assetstoreIds}})
        if fileCount > LARGE_ASSETSTORE_FILES:
            # Join items to folders in the database by appending every item's
            # folder and grouping by item.  This avoids sending a row per item
            # from the server.  For a few files, looking up their items is
            # faster than reading every item.
            joined = pipeline + [
                {'$unionWith': {'coll': Item().name,
                                'pipeline': [{'$project': {'folderId': 1}}]}},
                {'$group': {'_id': '$_id', 'size': {'$sum': '$size'}, 'n': {'$sum': '$n'},
                            'folderId': {'$max': '$folderId'}}},
                {'$match': {'n': {'$gt': 0}}},
                {'$group': {'_id': '$folderId', 'size': {'$sum': '$size'},
                            'n': {'$sum': '$n'}}},
            ]
            for row in File().collection.aggregate(joined, allowDiskUse=True):
                target = orphaned if row['_id'] is None else folderDirect[row['_id']]
                _add(target, row['size'], row['n'])
            return folderDirect, orphaned
        itemTotals = {row['_id']: [row['size'], row['n']]
                      for row in File().collection.aggregate(pipeline, allowDiskUse=True)}
        self._addItemFiles(itemTotals, folderDirect, orphaned)
        return folderDirect, orphaned

    def _attachedFileList(self, match):
        """
        List each file attached to a resource.  Files attached to items are
        also counted with item files, but are listed so that the files of an
        item can be reported without scanning for attachments.

        :returns: a list of (file id, attached type, attached id, size, True
            if the file also belongs to an item).
        """
        query = dict(match, attachedToId={'$ne': None})
        return [(doc['_id'], _attachedType(doc.get('attachedToType')), doc['attachedToId'],
                 doc.get('size') or 0, doc.get('itemId') is not None)
                for doc in File().collection.find(
                    query, {'size': 1, 'itemId': 1, 'attachedToType': 1, 'attachedToId': 1},
                    batch_size=BATCH_SIZE)]

    def _addAttachedFiles(self, attached):
        """
        Record attached files that are counted.

        :param attached: a list from _attachedFileList.
        """
        for fileId, attachedType, attachedId, size, inItem in attached:
            if fileId in self.duplicates:
                continue
            if attachedType in NODE_TYPES:
                self.attachedFiles[(attachedType, attachedId)].append((size, fileId))
            elif not inItem:
                _add(self.otherAttached, size, 1)

    def _unownedFiles(self, match):
        """
        Total files that belong to neither an item nor another resource.

        :returns: [size, count]
        """
        pipeline = [
            {'$match': dict(match, itemId=None, attachedToId=None)},
            {'$group': {'_id': None, 'size': {'$sum': '$size'}, 'n': {'$sum': 1}}},
        ]
        total = _zero()
        for row in File().collection.aggregate(pipeline, allowDiskUse=True):
            _add(total, row['size'], row['n'])
        return total

    def _duplicateFiles(self, match):
        """
        Find files that share stored data with an older file in the same
        assetstore.

        :returns: a list of the duplicate files with their owners and sizes.
        """
        # Assetstores whose adapters identify stored data by the same fields
        # are checked together.
        storesByFields = collections.defaultdict(list)
        for assetstore in self.filters.assetstores:
            try:
                adapter = assetstore_utilities.getAssetstoreAdapter(assetstore, instance=False)
            except NoAssetstoreAdapter:
                continue
            keyFields = tuple(getattr(adapter, 'fileStorageKeyFields', list)())
            if keyFields:
                storesByFields[keyFields].append(assetstore['_id'])
        duplicates = []
        for keyFields, assetstoreIds in storesByFields.items():
            duplicates.extend(self._duplicatesByFields(
                dict(match, assetstoreId={'$in': assetstoreIds}), keyFields))
        return duplicates

    def _duplicatesByFields(self, match, keyFields):
        """
        Find duplicate files among files whose stored data is identified by
        the specified fields.
        """
        query = dict(match)
        for field in keyFields:
            query[field] = {'$ne': None}
        storageKey = {field: '$' + field for field in keyFields}
        storageKey['_assetstoreId'] = '$assetstoreId'
        pipeline = [
            {'$match': query},
            {'$group': {
                '_id': storageKey,
                'n': {'$sum': 1},
                'files': {'$push': {'_id': '$_id', 'i': '$itemId', 't': '$attachedToType',
                                    'a': '$attachedToId', 's': '$size'}},
            }},
            {'$match': {'n': {'$gt': 1}}},
        ]
        duplicates = []
        for row in File().collection.aggregate(pipeline, allowDiskUse=True):
            files = sorted(row['files'], key=lambda doc: doc['_id'])
            duplicates.extend(files[1:])
        return duplicates

    def _removeDuplicates(self, duplicates, folderDirect):
        """
        Subtract duplicate files that were counted with item files or as
        unowned files.  Duplicates attached to other resources were already
        skipped.
        """
        itemTotals = collections.defaultdict(_zero)
        for doc in duplicates:
            itemId = doc.get('i')
            if itemId is None and self.filters.attached and doc.get('t') == 'item':
                itemId = doc.get('a')
            size = doc.get('s') or 0
            if itemId is not None:
                _add(itemTotals[itemId], size, 1)
            elif doc.get('a') is None:
                _add(self.orphaned, -size, -1)
        self._addItemFiles(itemTotals, folderDirect, self.orphaned, sign=-1)

    def _folderParents(self, folderIds):
        """
        Load the parents of the specified folders and all of their ancestors.

        :param folderIds: an iterable of folder ids.
        :returns: a dictionary of folder id to (parent type, parent id) for
            folders that exist.
        """
        parents = {}
        needed = set(folderIds)
        while needed:
            found = {}
            for chunk in _chunks(needed):
                for doc in Folder().collection.find(
                        {'_id': {'$in': chunk}}, {'parentCollection': 1, 'parentId': 1}):
                    found[doc['_id']] = (doc.get('parentCollection'), doc.get('parentId'))
            parents.update(found)
            needed = {parentId for parentType, parentId in found.values()
                      if parentType == 'folder' and parentId not in parents}
        return parents

    def _compute(self):
        match = self.filters.match()
        # These queries are independent and mostly run in the database, so run
        # them at the same time.
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            duplicatesFuture = (pool.submit(self._duplicateFiles, match)
                                if self.filters.dedup else None)
            attachedFuture = (pool.submit(self._attachedFileList, match)
                              if self.filters.attached else None)
            folderDirect, orphaned = self._itemFileTotals(match)
            _add(self.orphaned, *orphaned)
            _add(self.orphaned, *self._unownedFiles(match))
            duplicates = duplicatesFuture.result() if duplicatesFuture else []
            attached = attachedFuture.result() if attachedFuture else []
        self.duplicates.update(doc['_id'] for doc in duplicates)
        self._addAttachedFiles(attached)
        self._removeDuplicates(duplicates, folderDirect)

        for (attachedType, attachedId), files in self.attachedFiles.items():
            size = sum(entry[0] for entry in files)
            if attachedType == 'folder':
                _add(folderDirect[attachedId], size, len(files))
                _add(self.folderAttached[attachedId], size, len(files))
            elif attachedType in ROOT_TYPES:
                _add(self.rootAttached[(attachedType, attachedId)], size, len(files))
                _add(self.rootTotals[(attachedType, attachedId)], size, len(files))

        parents = self._folderParents(
            folderId for folderId, (size, count) in folderDirect.items() if count > 0)
        for folderId, (size, count) in folderDirect.items():
            if count <= 0:
                continue
            chain = []
            current = folderId
            root = None
            while current in parents and len(chain) < MAX_FOLDER_DEPTH:
                chain.append(current)
                parentType, parentId = parents[current]
                if parentType in ROOT_TYPES:
                    root = (parentType, parentId)
                    break
                if parentType != 'folder':
                    break
                current = parentId
            if root is None:
                _add(self.orphaned, size, count)
                self.folderAttached.pop(folderId, None)
                continue
            for chainId in chain:
                _add(self.folderTotals[chainId], size, count)
            _add(self.rootTotals[root], size, count)

        self._removeMissingRoots()
        for folderId in self.folderTotals:
            self.folderChildren[parents[folderId]].append(folderId)

    def _removeMissingRoots(self):
        """
        Count data under users or collections that no longer exist as
        orphaned.  Folders under missing roots keep their totals, but are only
        listed as children of the missing root, so they are never reported.
        """
        for rootType, model in (('user', User()), ('collection', Collection())):
            ids = [rootId for (keyType, rootId) in self.rootTotals if keyType == rootType]
            existing = set()
            for chunk in _chunks(ids):
                existing.update(doc['_id'] for doc in model.collection.find(
                    {'_id': {'$in': chunk}}, {'_id': 1}))
            for rootId in set(ids) - existing:
                size, count = self.rootTotals.pop((rootType, rootId))
                _add(self.orphaned, size, count)
                self.rootAttached.pop((rootType, rootId), None)

    def subtreeFolders(self, parentType, parentId):
        """
        Get the ids of the folders with data under a node, including the node
        itself if it is a folder.
        """
        result = [parentId] if parentType == 'folder' else []
        pending = [(parentType, parentId)]
        while pending:
            children = self.folderChildren.get(pending.pop(), [])
            result.extend(children)
            pending.extend(('folder', child) for child in children)
        return result

    def itemFiles(self, itemIds, fields):
        """
        Yield the counted files of a list of items, including attached files.

        :param itemIds: a list of item ids.
        :param fields: the file fields to return.
        """
        match = self.filters.match()
        for chunk in _chunks(itemIds):
            for doc in File().collection.find(
                    dict(match, itemId={'$in': chunk}), fields, batch_size=BATCH_SIZE):
                if doc['_id'] not in self.duplicates:
                    yield doc
        attachedIds = [fileId for itemId in itemIds
                       for size, fileId in self.attachedFiles.get(('item', itemId), ())]
        for chunk in _chunks(attachedIds):
            yield from File().collection.find({'_id': {'$in': chunk}}, fields)

    def itemTotals(self, itemIds):
        """
        Compute the storage used by each of a list of items.

        :param itemIds: a list of item ids.
        :returns: a dictionary of item id to [size, count] for items that use
            storage.
        """
        totals = collections.defaultdict(_zero)
        for chunk in _chunks(itemIds):
            for doc in File().collection.find(
                    dict(self.filters.match(), itemId={'$in': chunk}),
                    {'itemId': 1, 'size': 1}, batch_size=BATCH_SIZE):
                if doc['_id'] not in self.duplicates:
                    _add(totals[doc['itemId']], doc.get('size') or 0, 1)
        for itemId in itemIds:
            for size, _fileId in self.attachedFiles.get(('item', itemId), ()):
                _add(totals[itemId], size, 1)
        return totals

    def _largest(self, query, count):
        """
        Find the largest counted files matching a query.
        """
        limit = count
        while True:
            docs = list(File().collection.aggregate([
                {'$match': query},
                {'$sort': {'size': -1, '_id': 1}},
                {'$limit': limit},
                {'$project': _FILE_FIELDS},
            ], allowDiskUse=True))
            kept = [doc for doc in docs if doc['_id'] not in self.duplicates]
            if len(kept) >= count or len(docs) < limit:
                return kept[:count]
            limit *= 4

    def topFiles(self, itemChunks, attachedOwners, count):
        """
        Find the largest files in scope.

        :param itemChunks: None for all files in scope, or a list of lists of
            item ids whose files are considered.
        :param attachedOwners: a list of (type, id) of resources whose
            attached files are considered.
        :param count: the number of files to return.
        :returns: a list of file documents, largest first.
        """
        if count <= 0:
            return []
        match = self.filters.match()
        results = []
        if itemChunks is None:
            results.extend(self._largest(match, count))
        else:
            for chunk in itemChunks:
                results.extend(self._largest(dict(match, itemId={'$in': chunk}), count))
        candidates = heapq.nlargest(count, (
            entry for owner in attachedOwners for entry in self.attachedFiles.get(owner, ())))
        if candidates:
            results.extend(File().collection.find(
                {'_id': {'$in': [fileId for size, fileId in candidates]}}, _FILE_FIELDS))
        results.sort(key=lambda doc: (-(doc.get('size') or 0), doc['_id']))
        return results[:count]


def clearCache():
    """
    Discard all cached usage summaries.
    """
    with _cacheLock:
        _cache.clear()


def _getSummary(filters, refresh=False):
    key = filters.key
    with _cacheLock:
        lock = _computeLocks.setdefault(key, threading.Lock())
    with lock:
        with _cacheLock:
            summary = _cache.get(key)
            if summary is not None and not refresh and summary.expires > time.time():
                _cache.move_to_end(key)
                return summary
        summary = _Summary(filters)
        with _cacheLock:
            _cache[key] = summary
            _cache.move_to_end(key)
            while len(_cache) > CACHE_ENTRIES:
                _cache.popitem(last=False)
        return summary


def _names(nodeType, ids):
    """
    Get display names for a list of resources.

    :returns: a dictionary of id to name.
    """
    if not ids:
        return {}
    model = {'user': User, 'collection': Collection, 'folder': Folder,
             'item': Item, 'file': File}[nodeType]()
    field = 'login' if nodeType == 'user' else 'name'
    names = {}
    for chunk in _chunks(ids):
        for doc in model.collection.find({'_id': {'$in': chunk}}, {field: 1}):
            names[doc['_id']] = doc.get(field)
    return names


def _node(nodeType, nodeId, name, total, drillable):
    return {
        'type': nodeType,
        '_id': nodeId,
        'name': name,
        'size': total[0],
        'count': total[1],
        'drillable': drillable,
    }


def _breadcrumbs(parentType, parent):
    if parentType in ROOT_TYPES:
        path = []
    elif parentType == 'folder':
        path = Folder().parentsToRoot(parent, force=True)
    else:
        path = Item().parentsToRoot(parent, force=True)
    path = path + [{'type': parentType, 'object': parent}]
    return [{
        'type': entry['type'],
        '_id': entry['object']['_id'],
        'name': entry['object'].get('login' if entry['type'] == 'user' else 'name'),
    } for entry in path]


def _resourceForFile(doc):
    """
    Get the resource that a file should link to: its item, or the resource it
    is attached to.
    """
    if doc.get('itemId') is not None:
        return 'item', doc['itemId']
    attachedType = _attachedType(doc.get('attachedToType'))
    if attachedType in NODE_TYPES and doc.get('attachedToId') is not None:
        return attachedType, doc['attachedToId']
    return None, None


def _resourcePath(resourceType, resourceId):
    """
    Get the path of a resource, or None if it or one of its ancestors no
    longer exists.
    """
    doc = ModelImporter.model(resourceType).load(resourceId, force=True)
    if doc is None:
        return None
    try:
        return path_util.getResourcePath(resourceType, doc, force=True)
    except TypeError:
        # An ancestor is missing
        return None


def _describeFiles(docs):
    """
    Convert file documents to report entries, including the name and path of
    the resource each file belongs to.
    """
    resources = collections.defaultdict(set)
    for doc in docs:
        resourceType, resourceId = _resourceForFile(doc)
        if resourceType:
            resources[resourceType].add(resourceId)
    names = {resourceType: _names(resourceType, list(ids))
             for resourceType, ids in resources.items()}
    paths = {(resourceType, resourceId): _resourcePath(resourceType, resourceId)
             for resourceType, ids in resources.items() for resourceId in ids}
    results = []
    for doc in docs:
        resourceType, resourceId = _resourceForFile(doc)
        results.append({
            '_id': doc['_id'],
            'name': doc.get('name'),
            'size': doc.get('size') or 0,
            'assetstoreId': doc.get('assetstoreId'),
            'imported': bool(doc.get('imported')),
            'attached': doc.get('itemId') is None,
            'resourceType': resourceType,
            'resourceId': resourceId,
            'resourceName': names.get(resourceType, {}).get(resourceId),
            'resourcePath': paths.get((resourceType, resourceId)),
        })
    return results


def _topFiles(summary, parentType, parent, count):
    """
    Find the largest files under a node.
    """
    if parentType is None:
        return summary.topFiles(None, [], count)
    if parentType == 'item':
        return summary.topFiles([[parent['_id']]], [('item', parent['_id'])], count)
    folderIds = summary.subtreeFolders(parentType, parent['_id'])
    owners = [('folder', folderId) for folderId in folderIds]
    if parentType in ROOT_TYPES:
        owners.append((parentType, parent['_id']))
    itemIds = []
    for chunk in _chunks(folderIds):
        itemIds.extend(doc['_id'] for doc in Item().collection.find(
            {'folderId': {'$in': chunk}}, {'_id': 1}, batch_size=BATCH_SIZE))
    owners.extend(('item', itemId) for itemId in itemIds)
    return summary.topFiles(list(_chunks(itemIds)), owners, count)


def _children(summary, parentType, parent):
    """
    Get the report entries for the children of a node, and the node's total.
    """
    children = []
    if parentType is None:
        for rootType in ROOT_TYPES:
            ids = [rootId for (keyType, rootId) in summary.rootTotals if keyType == rootType]
            names = _names(rootType, ids)
            children.extend(_node(rootType, rootId, names.get(rootId), summary.rootTotals[
                (rootType, rootId)], True) for rootId in ids)
        if summary.orphaned[1]:
            children.append(_node('orphaned', None, 'Orphaned files', summary.orphaned, False))
        if summary.otherAttached[1]:
            children.append(_node(
                'otherAttached', None, 'Files attached to other resources',
                summary.otherAttached, False))
        total = _zero()
        for child in children:
            _add(total, child['size'], child['count'])
        return children, total

    parentId = parent['_id']
    if parentType == 'item':
        total = _zero()
        for doc in summary.itemFiles([parentId], {'name': 1, 'size': 1, 'itemId': 1}):
            node = _node('file', doc['_id'], doc.get('name'), [doc.get('size') or 0, 1], False)
            node['attached'] = doc.get('itemId') is None
            children.append(node)
            _add(total, node['size'], 1)
        return children, total

    folderIds = summary.folderChildren.get((parentType, parentId), [])
    names = _names('folder', folderIds)
    children.extend(_node('folder', folderId, names.get(folderId), summary.folderTotals[
        folderId], True) for folderId in folderIds)
    if parentType == 'folder':
        itemIds = [doc['_id'] for doc in Item().collection.find(
            {'folderId': parentId}, {'_id': 1}, batch_size=BATCH_SIZE)]
        itemTotals = summary.itemTotals(itemIds)
        names = _names('item', list(itemTotals))
        children.extend(_node('item', itemId, names.get(itemId), itemTotal, True)
                        for itemId, itemTotal in itemTotals.items())
        attached = summary.folderAttached.get(parentId)
        total = summary.folderTotals.get(parentId, _zero())
    else:
        attached = summary.rootAttached.get((parentType, parentId))
        total = summary.rootTotals.get((parentType, parentId), _zero())
    if attached and attached[1]:
        children.append(_node('attached', None, 'Attached files', attached, False))
    return children, list(total)


def getUsage(assetstore=None, parentType=None, parent=None, attached=True, dedup=False,
             source='all', limit=100, topFiles=20, refresh=False):
    """
    Report the storage used under a node of the data hierarchy.

    :param assetstore: the assetstore to report on, or None for all
        assetstores.
    :param parentType: None to list users and collections, or one of 'user',
        'collection', 'folder', or 'item' to list the children of that
        resource.
    :param parent: the resource document if parentType is specified.
    :param attached: if True, include files attached to resources other than
        items, such as thumbnails, as part of the resource they are attached
        to.
    :param dedup: if True, count stored data shared by several files once.
    :param source: 'all', 'uploaded', or 'imported' files.
    :param limit: the maximum number of children to list.  The remainder is
        summarized.  0 lists all children.
    :param topFiles: the number of largest files under the node to list.
    :param refresh: if True, recompute the summary instead of using a cached
        one.
    :returns: a dictionary with the node, its breadcrumbs, its children
        sorted by size, a summary of children past the limit, and the largest
        files.
    """
    if parentType is not None and parentType not in NODE_TYPES:
        raise ValidationException('Invalid parent type.', 'parentType')
    filters = _Filters(assetstore, attached, dedup, source)
    summary = _getSummary(filters, refresh)

    children, total = _children(summary, parentType, parent)
    children.sort(key=lambda child: (-child['size'], -child['count'], str(child['name'])))
    other = _zero()
    otherNodes = 0
    if limit and len(children) > limit:
        for child in children[limit:]:
            _add(other, child['size'], child['count'])
        otherNodes = len(children) - limit
        children = children[:limit]

    breadcrumbs = [] if parentType is None else _breadcrumbs(parentType, parent)
    node = dict(breadcrumbs[-1]) if breadcrumbs else {'type': None, '_id': None, 'name': None}
    node['size'], node['count'] = total

    return {
        'assetstoreId': filters.assetstore['_id'] if filters.assetstore else None,
        'attached': filters.attached,
        'dedup': filters.dedup,
        'source': filters.source,
        'computed': summary.computed,
        'elapsed': round(summary.elapsed, 3),
        'node': node,
        'breadcrumbs': breadcrumbs,
        'children': children,
        'other': {'size': other[0], 'count': other[1], 'nodes': otherNodes},
        'topFiles': _describeFiles(_topFiles(summary, parentType, parent, topFiles)),
    }
