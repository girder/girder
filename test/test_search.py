import pytest

from girder.constants import AccessType
from girder.exceptions import AccessException, ValidationException
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.item import Item
from girder.utility.search import hierarchySearchPipeline


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
