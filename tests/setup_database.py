# -*- coding: utf-8 -*-
import mimetypes
import os
import tempfile
import warnings

from girder.exceptions import GirderException
from girder.settings import SettingKey
from girder.utility.model_importer import ModelImporter

warnings.warn(
    'setup_database.py is only meant for test fixtures, not for provisioning.'
    "\nSee Girder's ansible client for a deployment solution: "
    'https://github.com/girder/girder/tree/master/devops/ansible-role-girder/library'
)

#: A prefix for all relative file paths
prefix = '.'


def resolvePath(path):
    """Resolve a path to an absolute path string."""
    global prefix
    if os.path.isabs(path):
        return path
    return os.path.abspath(os.path.join(prefix, path))


def loadModel(kind):
    """Load a model class from its name."""
    return ModelImporter.model(kind)


def setAssetstore(name=None):
    """Set the assetstore that will be used for all files.

    The default behavior of this function is to assert that
    an assetstore exists, if not it will create a new filesystem
    assetstore with the name ``test``.  Optionally, a name
    can be provided to pick (or create) a specific assetstore.

    :param name: The name of the assetstore
    :type name: str
    """
    assetstore = None
    assetstoreModel = loadModel('assetstore')
    if not name:
        try:
            assetstore = assetstoreModel.getCurrent()
        except GirderException:
            pass
    else:
        for a in assetstoreModel.list():
            if name == a['name']:
                assetstore = a

    if assetstore is None:
        dir = tempfile.mkdtemp()
        assetstore = assetstoreModel.createFilesystemAssetstore(
            name or 'test', dir)

    assetstore['current'] = True
    assetstoreModel.save(assetstore)


def addCreator(spec, parent=None):
    """Inject a creator into document spec.

    This function mutates the input spec setting the ``creator``
    key to a valid user document.  If the key is set to a
    name, then the document will be queried from the global
    ``users`` cache, otherwise it will use the creator of
    the parent document.

    :param spec: The document to mutate
    :type spec: dict
    :param parent: The parent of current document
    :type parent: dict
    """
    userModel = loadModel('user')
    if 'creator' in spec:
        spec['creator'] = userModel.findOne({'login': spec['creator'].lower()}, force=True)
    elif parent is not None:

        if parent.get('_modelType') == 'user':
            # if the parent is a user, then use that as the creator
            # (users don't have creators)
            spec['creator'] = parent
        elif parent.get('creatorId'):
            # otherwise, use the creator of the parent
            spec['creator'] = userModel.load(parent.get('creatorId'), force=True)
    else:
        # if all else fails, just use any user for the creator
        spec['creator'] = userModel.findOne({}, force=True)

        if spec['creator'] is None:
            raise Exception('At least one user must be provided in the spec')

    if spec.get('creator') is None:
        raise Exception('Could not find the requested creator')


def createUser(defaultFolders=False, **args):
    """Create a user document from a user spec.

    As a side effect of this function, the created user will be
    cached in a global dictionary to be used by :py:func:`addCreator`.
    Keyword arguments are passed directly to the ``createUser``
    function.

    The default behavior is to **not** create the default public and
    private folders.  Automatically created folders cannot be used
    by this module as a parent for new folders and items.

    :param defaultFolders: Create default public and private folders
    :type defaultFolders: bool
    :returns: The generated user document
    """
    settingModel = loadModel('setting')
    userModel = loadModel('user')
    if not defaultFolders:
        settingModel.set(SettingKey.USER_DEFAULT_FOLDERS, 'none')
    user = userModel.createUser(**args)
    if not defaultFolders:
        settingModel.unset(SettingKey.USER_DEFAULT_FOLDERS)
    return user


def createCollection(**args):
    """Create a collection document from a collection spec.

    Keyword arguments are passed directly to the ``createCollection``
    function.

    :returns: The generated collection document
    """
    addCreator(args)
    collectionModel = loadModel('collection')
    return collectionModel.createCollection(**args)


def createFolder(parent, **args):
    """Create a folder document from a folder spec.

    The parent type can be any of ``collection``, ``folder``, or
    ``user``.  The parent is automatically injected into
    the keyword arguments.

    :param parent: The parent document
    :type parent: dict
    :returns: The generated folder document
    """
    addCreator(args, parent)
    folderModel = loadModel('folder')
    args['parentType'] = parent['_modelType']
    return folderModel.createFolder(parent, **args)


def createItem(parent, **args):
    """Create an item document from an item spec.

    The parent folder document must be provided and is injected
    automatically into the keyword arguments.

    :param parent: The parent folder
    :type parent: dict
    :returns: The generated item document
    """
    addCreator(args, parent)
    itemModel = loadModel('item')
    args['folder'] = parent
    return itemModel.createItem(**args)


def createFile(parent, path, **args):
    """Create a file document from a file path.

    The provided path should resolve to a valid file.  The
    ``size`` and ``mimeType`` of the file will be automatically
    resolved from this path.

    :param parent: The parent item
    :type parent: dict
    :param path: The local path to a file
    :type path: str
    :returns: The generated file document
    """
    addCreator(args, parent)
    uploadModel = loadModel('upload')

    path = resolvePath(path)
    args['parentType'] = 'item'
    args['parent'] = parent
    args['user'] = args.pop('creator')
    args['size'] = os.path.getsize(path)
    args.setdefault('reference', 'setup_database')

    if 'name' not in args:
        args['name'] = os.path.basename(path)

    if not args.get('mimeType'):
        args['mimeType'] = mimetypes.guess_type(path)[0]

    with open(path, 'rb') as f:
        return uploadModel.uploadFromFile(f, **args)


dispatch = {
    'user': createUser,
    'collection': createCollection,
    'folder': createFolder,
    'item': createItem,
    'file': createFile
}


def createDocument(type, node):
    """Create a generic document type from a spec.

    :param type: The type of document to create
    :type type: str
    :param node: The document spec
    :type node: dict
    :returns: An objected describing the document's children
    """
    # automatically generate children specs from a local path
    path = node.pop('import', None)
    if path:
        importRecursive(type, node, path)

    # create the return object with all possible children
    children = {
        'folder': node.pop('folders', []),
        'item': node.pop('items', []),
        'file': node.pop('files', [])
    }

    # remove invalid child types
    if type in ['user', 'collection']:
        del children['item']
        del children['file']
    elif type == 'folder':
        del children['file']
    elif type == 'item':
        del children['folder']
        del children['item']

    # generate the document
    doc = dispatch[type](**node)

    # set the type for certain models (collection) that don't do it
    # on their own
    doc['_modelType'] = type

    # inject this document as the parent for all child specs
    for childType in children:
        children[childType] = [
            dict(parent=doc, **child) for child in children[childType]
        ]

    return children


def createRecursive(type, node):
    """Generate all documents from a given node recursively.

    :param type: The type of the root node
    :type type: str
    :param node: The root node spec
    :type node: dict
    """
    children = createDocument(type, node)
    for childType in children:
        for childNode in children[childType]:
            createRecursive(childType, childNode)


def createUsers(users):
    """Create a list of users.

    This method is special because we need to generate all users
    before any other type in order to inject the ``creator``
    argument correctly.

    :param users: A list of user specs
    :type users: list
    :returns: A list of all child documents for all users
    """
    folders = []
    for user in users:
        for folder in user.get('folders', []):
            # By default set the creator under a user to that user
            folder.setdefault('creator', user['login'])

        folders.extend(createDocument('user', user)['folder'])
    return folders


def importRecursive(type, parent, root):
    """Generate a document tree from a local path.

    The parent object will be mutated to append the folders and
    directories contained in the provided local path.

    :param type: The parent node type
    :type type: str
    :param parent: The parent document
    :type parent: dict
    :param root: The local path where the import will begin
    :type root: str
    """
    root = resolvePath(root)
    folders = {root: parent}

    for wroot, dirs, files in os.walk(root, followlinks=True):
        parent = folders[wroot]
        parent.setdefault('folders', [])
        parent.setdefault('items', [])

        for dir in dirs:
            path = os.path.join(wroot, dir)
            folder = {
                'name': dir
            }
            folders[path] = folder
            parent['folders'].append(folder)

        for file in files:
            path = os.path.join(wroot, file)

            parent['items'].append({
                'name': file,
                'files': [{
                    'name': file,
                    'path': path
                }]
            })


def generate(spec):
    """Generate documents from a nested object."""
    global prefix
    prefix = spec.get('prefix', prefix)

    setAssetstore(spec.get('assetstore'))

    # users have to generated first
    spec['folders'] = createUsers(spec.get('users', []))

    for collection in spec.get('collections', []):
        createRecursive('collection', collection)

    for folder in spec.get('folders', []):
        createRecursive('folder', folder)


def main(file):
    """Load a file into memory and generate the documents it describes."""
    prefix = os.path.dirname(file)
    with open(file) as f:
        import yaml
        spec = yaml.safe_load(f)
        spec.setdefault('prefix', prefix)
        generate(spec)


# For standalone usage, this file can be called as a script to generate
# a testing environment.  You should provide an empty database as an
# environment variable.  For example:
#
#   GIRDER_MONGO_URI='mongodb://127.0.0.1:27017/import_test' python setup_database.py spec.yml
#   GIRDER_MONGO_URI='mongodb://127.0.0.1:27017/import_test' girder serve
if __name__ == '__main__':
    import sys
    main(sys.argv[1])
