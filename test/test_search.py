import json

import pytest

from girder.constants import AccessType
from girder.exceptions import AccessException, ValidationException
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.item import Item
from girder.utility import search
from girder.utility.search import hierarchySearchPipeline
from pytest_girder.assertions import assertStatus, assertStatusOk


@pytest.fixture
def tree(admin):
    """
    A small hierarchy to search within::

        collection "coll"                  collection "other"
        |-- top                            |-- elsewhere
            |-- (item) topItem                 |-- (item) elsewhereItem
            |-- mid
            │   |-- (item) midItem
            │   |-- deep
            │       |-- (item) deepItem
            |-- sibling
                |-- (item) siblingItem
    """
    coll = Collection().createCollection('coll', creator=admin, public=True)
    other = Collection().createCollection('other', creator=admin, public=True)
    folders = {}

    def folder(name, parent, parentType='folder'):
        folders[name] = Folder().createFolder(parent, name, parentType=parentType, creator=admin)
        return folders[name]

    folder('top', coll, 'collection')
    folder('mid', folders['top'])
    folder('deep', folders['mid'])
    folder('sibling', folders['top'])
    folder('elsewhere', other, 'collection')
    for name in ('top', 'mid', 'deep', 'sibling', 'elsewhere'):
        Item().createItem('%sItem' % name, creator=admin, folder=folders[name])
    yield {'coll': coll, 'other': other, **folders}


def _names(model, pipeline):
    return {doc['name'] for doc in model.collection.aggregate(pipeline)}


def testRestrictItemsToFolder(tree, admin):
    pipeline = hierarchySearchPipeline('folder', str(tree['mid']['_id']), admin)
    assert _names(Item(), pipeline) == {'midItem', 'deepItem'}


def testRestrictFoldersToFolder(tree, admin):
    # The folder being searched from is the container, not a result
    pipeline = hierarchySearchPipeline('folder', tree['top']['_id'], admin, resultType='folder')
    assert _names(Folder(), pipeline) == {'mid', 'deep', 'sibling'}


def testRestrictToCollection(tree, admin):
    pipeline = hierarchySearchPipeline('collection', tree['coll']['_id'], admin)
    assert len(pipeline) == 1
    assert _names(Item(), pipeline) == {'topItem', 'midItem', 'deepItem', 'siblingItem'}

    pipeline = hierarchySearchPipeline(
        'collection', tree['coll']['_id'], admin, resultType='folder')
    assert _names(Folder(), pipeline) == {'top', 'mid', 'deep', 'sibling'}


def testRestrictToInaccessibleFolder(tree, admin, user):
    private = Folder().createFolder(tree['top'], 'private', creator=admin, public=False)
    with pytest.raises(AccessException):
        hierarchySearchPipeline('folder', private['_id'], user)


def testRestrictDoesNotCheckAccessOnTheWayUp(tree, admin, user):
    # The walk ignores permissions; the search using the stages checks them.
    private = Folder().createFolder(tree['top'], 'private', creator=admin, public=False)
    openBelow = Folder().createFolder(private, 'openBelow', creator=admin, public=True)
    Item().createItem('privateItem', creator=admin, folder=private)
    Item().createItem('openItem', creator=admin, folder=openBelow)

    pipeline = hierarchySearchPipeline('folder', tree['top']['_id'], user)
    assert {'privateItem', 'openItem'} <= _names(Item(), pipeline)

    # With item permissions applied, only the item in the private folder is dropped.
    permissionStages = [
        {'$lookup': {
            'from': 'folder', 'localField': 'folderId', 'foreignField': '_id', 'as': '__parent'}},
        {'$match': Item().permissionClauses(user, AccessType.READ, '__parent.')},
    ]
    names = _names(Item(), pipeline + permissionStages)
    assert 'privateItem' not in names
    assert 'openItem' in names


def testRestrictDeepTree(tree, admin):
    parent = tree['top']
    chain = []
    for depth in range(50):
        parent = Folder().createFolder(parent, 'level%d' % depth, creator=admin)
        chain.append(parent)
    Item().createItem('bottomItem', creator=admin, folder=chain[-1])

    for start in (tree['top'], chain[0], chain[25], chain[-1]):
        pipeline = hierarchySearchPipeline('folder', start['_id'], admin)
        assert 'bottomItem' in _names(Item(), pipeline)
    assert 'bottomItem' not in _names(
        Item(), hierarchySearchPipeline('folder', tree['sibling']['_id'], admin))


def testRestrictNestedDocuments(tree, admin):
    # Documents that refer to items, rather than items
    pipeline = [
        {'$lookup': {'from': 'item', 'localField': '_id', 'foreignField': '_id', 'as': 'item'}},
        {'$unwind': '$item'},
    ] + hierarchySearchPipeline('folder', tree['mid']['_id'], admin, prefix='item.')
    assert _names(Item(), pipeline) == {'midItem', 'deepItem'}


def testRestrictUsesOnlyMongo36Stages(tree, admin):
    # Girder supports MongoDB 3.6, which lacks later stages like $unset.
    for parentType, parent in (('folder', tree['mid']), ('collection', tree['coll'])):
        stages = hierarchySearchPipeline(parentType, parent['_id'], admin)
        assert {next(iter(stage)) for stage in stages} <= {'$match', '$graphLookup', '$project'}


@pytest.mark.parametrize('args,field', [
    (('group', 'aaaaaaaaaaaaaaaaaaaaaaaa'), 'parentType'),
    (('folder', 'not-an-id'), 'parentId'),
])
def testRestrictInvalidParent(admin, args, field):
    with pytest.raises(ValidationException) as exc:
        hierarchySearchPipeline(*args, admin)
    assert exc.value.field == field


def testRestrictInvalidResultType(admin):
    with pytest.raises(ValidationException) as exc:
        hierarchySearchPipeline(
            'collection', 'aaaaaaaaaaaaaaaaaaaaaaaa', admin, resultType='annotation')
    assert exc.value.field == 'resultType'


@pytest.fixture
def scans(admin):
    """
    Matches for "scan", mostly outside the folder being searched::

        collection "scans"
        |-- outside
        │   |-- (items) scan-away-0...scan-away-5
        |-- inside
            |-- (items) scan-here-0...scan-here-2
            |-- scan-folder
            |-- private
                |-- (item) scan-private

    The items outside come first, both by creation order and by name.
    """
    coll = Collection().createCollection('scans', creator=admin, public=True)
    outside = Folder().createFolder(coll, 'outside', parentType='collection', creator=admin)
    inside = Folder().createFolder(coll, 'inside', parentType='collection', creator=admin)
    for i in range(6):
        Item().createItem('scan-away-%d' % i, creator=admin, folder=outside)
    for i in range(3):
        Item().createItem('scan-here-%d' % i, creator=admin, folder=inside)
    Folder().createFolder(inside, 'scan-folder', creator=admin)
    private = Folder().createFolder(inside, 'private', creator=admin, public=False)
    Item().createItem('scan-private', creator=admin, folder=private)
    yield {'coll': coll, 'outside': outside, 'inside': inside, 'private': private}


def _unrestrictedPrefixSearch(query, types, user, level, limit, offset):
    return search._commonSearchModeHandler('prefix', query, types, user, level, limit, offset)


@pytest.fixture(autouse=True)
def pluginSearchModes(monkeypatch):
    """Plugin-like search modes that don't restrict their own queries, read in small batches."""
    calls = []

    def plainHandler(query, types, user, level, limit, offset):
        return _unrestrictedPrefixSearch(query, types, user, level, limit, offset)

    def kwargsHandler(query, types, user, level, limit, offset, **kwargs):
        calls.append(kwargs)
        return _unrestrictedPrefixSearch(query, types, user, level, limit, offset)

    monkeypatch.setattr(search, '_FALLBACK_SEARCH_BATCH_SIZE', 3)
    search.addSearchMode('plainPrefix', plainHandler)
    search.addSearchMode('kwargsPrefix', kwargsHandler)
    yield calls
    search.removeSearchMode('plainPrefix')
    search.removeSearchMode('kwargsPrefix')


ALL_MODES = ['plainPrefix', 'kwargsPrefix']


def _search(server, user, parent, mode, parentType='folder', types=('item',), **params):
    resp = server.request(path='/resource/search', user=user, params={
        'q': 'scan', 'mode': mode, 'types': json.dumps(list(types)),
        'parentType': parentType, 'parentId': str(parent['_id']), **params})
    assertStatusOk(resp)
    return {type: [doc['name'] for doc in docs] for type, docs in resp.json.items()}


@pytest.mark.parametrize('mode', ALL_MODES)
@pytest.mark.parametrize('asAdmin', [True, False])
def testSearchRestrictedToFolder(server, scans, admin, user, asAdmin, mode):
    results = _search(
        server, admin if asAdmin else user, scans['inside'], mode,
        types=('item', 'folder'))
    expected = {'scan-here-0', 'scan-here-1', 'scan-here-2'}
    if asAdmin:
        expected.add('scan-private')
    assert set(results['item']) == expected
    assert results['folder'] == ['scan-folder']


@pytest.mark.parametrize('mode', ALL_MODES)
@pytest.mark.parametrize('asAdmin', [True, False])
def testSearchRestrictedPaging(server, scans, admin, user, asAdmin, mode):
    # Restricting happens before paging, so pages are full though the first matches are outside.
    pages = [
        _search(server, admin if asAdmin else user, scans['inside'], mode, limit=2,
                offset=offset)['item']
        for offset in (0, 2, 4)]
    assert [len(page) for page in pages] == [2, 1 + asAdmin, 0]
    found = pages[0] + pages[1]
    assert len(set(found)) == len(found)
    assert all(name.startswith('scan-here-') or name == 'scan-private' for name in found)


@pytest.mark.parametrize('mode', ALL_MODES)
def testSearchRestrictedToCollection(server, scans, admin, user, mode):
    other = Collection().createCollection('other', creator=admin, public=True)
    otherFolder = Folder().createFolder(other, 'elsewhere', parentType='collection', creator=admin)
    Item().createItem('scan-elsewhere', creator=admin, folder=otherFolder)

    results = _search(server, user, scans['coll'], mode, parentType='collection')
    assert set(results['item']) == {'scan-away-%d' % i for i in range(6)} | {
        'scan-here-%d' % i for i in range(3)}


@pytest.mark.parametrize('mode', ALL_MODES)
def testSearchRestrictedOtherTypes(server, scans, admin, mode):
    results = _search(
        server, admin, scans['inside'], mode, types=('item', 'collection', 'user', 'group'))
    assert results['collection'] == []
    assert results['user'] == []
    assert results['group'] == []
    assert len(results['item']) == 4


@pytest.mark.parametrize('mode', ALL_MODES)
def testSearchRestrictedToInaccessibleFolder(server, scans, user, mode):
    resp = server.request(path='/resource/search', user=user, params={
        'q': 'scan', 'mode': mode, 'types': json.dumps(['item']),
        'parentType': 'folder', 'parentId': str(scans['private']['_id'])})
    assertStatus(resp, 403)


def testSearchFallbackGetsNoNewArguments(server, scans, admin, pluginSearchModes):
    _search(server, admin, scans['inside'], 'kwargsPrefix')
    assert pluginSearchModes
    assert all(kwargs == {} for kwargs in pluginSearchModes)


@pytest.mark.parametrize('readLimit,expected', [
    # The six items outside the folder come first, so reading only four finds nothing
    (4, set()),
    # Reading eight finds only the first two inside
    (8, {'scan-here-0', 'scan-here-1'}),
    (search.FALLBACK_SEARCH_READ_LIMIT,
     {'scan-here-0', 'scan-here-1', 'scan-here-2', 'scan-private'}),
])
def testSearchFallbackReadLimit(server, scans, admin, monkeypatch, readLimit, expected):
    monkeypatch.setattr(search, 'FALLBACK_SEARCH_READ_LIMIT', readLimit)
    results = _search(server, admin, scans['inside'], 'plainPrefix')
    assert set(results['item']) == expected


def testSearchFastPathResultsAreChecked(server, scans, admin):
    def ignoringHandler(query, types, user, level, limit, offset, hierarchyPipeline=None):
        assert callable(hierarchyPipeline)
        return _unrestrictedPrefixSearch(query, types, user, level, limit, offset)

    search.addSearchMode('ignoringPrefix', ignoringHandler)
    try:
        results = _search(server, admin, scans['inside'], 'ignoringPrefix', limit=20)
    finally:
        search.removeSearchMode('ignoringPrefix')
    assert set(results['item']) == {'scan-here-0', 'scan-here-1', 'scan-here-2', 'scan-private'}


def testSearchFallbackUnexpectedResults(server, scans, admin):
    search.addSearchMode('listSearch', lambda query, types, user, level, limit, offset: [])
    try:
        results = _search(server, admin, scans['inside'], 'listSearch', types=('item', 'folder'))
    finally:
        search.removeSearchMode('listSearch')
    assert results == {'item': [], 'folder': []}


def testSearchFallbackOverlappingBatches(scans, admin):
    # A batch that repeats an earlier result isn't mistaken for the handler running out.
    docs = list(Item().find({'name': {'$regex': '^scan-'}}, sort=[('name', 1)]))

    def handler(query, types, user, level, limit, offset):
        page = docs[offset:offset + limit]
        return {'item': docs[:1] + page[1:] if offset == 3 else page}

    results = search.runSearch(
        handler, 'scan', ['item'], admin, AccessType.READ, 10, 0, 'folder', scans['inside']['_id'])
    assert {doc['name'] for doc in results['item']} == {
        'scan-here-0', 'scan-here-1', 'scan-here-2', 'scan-private'}


def testSearchFallbackUnusableIds(scans, admin):
    # Results without a valid _id are dropped
    inside = list(Item().find({'folderId': scans['inside']['_id']}))

    def handler(query, types, user, level, limit, offset):
        return {'item': [] if offset else [{'_id': 'not-an-id'}, {'name': 'no id'}] + inside}

    results = search.runSearch(
        handler, 'scan', ['item'], admin, AccessType.READ, 10, 0, 'folder', scans['inside']['_id'])
    assert {doc['name'] for doc in results['item']} == {'scan-here-0', 'scan-here-1', 'scan-here-2'}


def testSearchUnrestrictedPluginModeUnchanged(server, scans, admin, pluginSearchModes):
    resp = server.request(path='/resource/search', user=admin, params={
        'q': 'scan', 'mode': 'kwargsPrefix', 'types': json.dumps(['item']), 'limit': 20})
    assertStatusOk(resp)
    assert len(resp.json['item']) == 10
    assert pluginSearchModes == [{}]
