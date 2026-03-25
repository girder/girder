import re

from girder.constants import AccessType
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item

from .parser import parse_json_desc, parse_xml_desc, parse_yaml_desc


def _split(name):
    """
    :param name: image name
    :type name: string
    """
    if ':' in name.split('/')[-1]:
        return name.rsplit(':', 1)
    return name.rsplit('@', 1)


class CLIItem:
    def __init__(self, item):
        self.item = item
        self._id = item['_id']
        self.name = item['name']
        meta = item['meta']
        self.type = meta['type']
        self.image = meta.get('image', 'UNKNOWN')
        self.digest = meta.get('digest', self.image)
        self.xml = meta['xml']
        if isinstance(self.xml, str):
            self.xml = self.xml.encode('utf8')

        self.restBasePath = self.image.replace(':', '_').replace('/', '_').replace('@', '_')

    def __str__(self):
        return 'CLIItem %s, image: %s, id: %s' % (self.name, self.image, self._id)

    @staticmethod
    def find(itemId, user):
        itemModel = Item()
        item = itemModel.load(itemId, user=user, level=AccessType.READ)
        if not item:
            return None
        return CLIItem(item)

    @staticmethod
    def findByName(image, name, user):
        image_regex = re.compile(re.escape(image).replace('_', '[_@:/]'))
        item = Item().findWithPermissions({
            'meta.image': {'$regex': image_regex},
            'name': name,
        }, user=user, level=AccessType.READ)

        item = next(item, None)

        if not item:
            return None
        return CLIItem(item)

    @staticmethod
    def _findAllItemImpl(user=None, extraQuery=None):
        itemModel = Item()
        q = {'meta.slicerCLIType': 'task'}

        if extraQuery:
            q.update(extraQuery)

        if user:
            items = itemModel.findWithPermissions(q, user=user, level=AccessType.READ)
        else:
            items = itemModel.find(q)

        return [CLIItem(item) for item in items]

    @staticmethod
    def findAllItems(user=None, baseFolder=None):
        if not baseFolder:
            return CLIItem._findAllItemImpl(user)

        folderModel = Folder()
        graphLookup = {
            'from': 'folder',
            'startWith': '$_id',
            'connectFromField': '_id',
            'connectToField': 'parentId',
            'as': 'children'
        }

        if user and not user['admin']:
            graphLookup['restrictSearchWithMatch'] = folderModel.permissionClauses(user,
                                                                                   AccessType.READ)

        # see https://docs.mongodb.com/manual/reference/operator/aggregation/graphLookup
        r = folderModel.collection.aggregate([
            {
                '$match': dict(_id=baseFolder['_id'])
            },
            {
                '$graphLookup': graphLookup
            },
            {
                '$project': {
                    'leaves': '$children._id',
                }
            }
        ])

        leaves = next(r)['leaves']

        return CLIItem._findAllItemImpl(user, {
            'folderId': {'$in': [baseFolder['_id']] + leaves}
        })


class DockerImageItem:
    def __init__(self, imageFolder, tagFolder, user):
        self.image = imageFolder['name']
        self.tag = tagFolder['name']
        self.name = '%s:%s' % (self.image, self.tag)
        self.imageFolder = imageFolder
        self.tagFolder = tagFolder
        self._id = self.tagFolder['_id']
        self.user = user
        self.name = '%s:%s' % (self.image, self.tag)
        self.digest = tagFolder['meta'].get('digest', self.name)

    def getCLIs(self):
        itemModel = Item()
        q = {
            'meta.slicerCLIType': 'task',
            'folderId': self.tagFolder['_id']
        }
        if self.user:
            items = itemModel.findWithPermissions(q, user=self.user, level=AccessType.READ)
        else:
            items = itemModel.find(q)

        return [CLIItem(item) for item in items]

    @staticmethod
    def find(tagFolderId, user):
        folderModel = Folder()
        tagFolder = folderModel.load(tagFolderId, user=user, level=AccessType.READ)
        if not tagFolder:
            return None
        imageFolder = folderModel.load(tagFolder['parentId'], user=user, level=AccessType.READ)
        return DockerImageItem(imageFolder, tagFolder, user)

    @staticmethod
    def findAllImages(user=None, baseFolder=None):
        folderModel = Folder()
        q = {'meta.slicerCLIType': 'image'}
        if baseFolder:
            q['parentId'] = baseFolder['_id']

        if user:
            imageFolders = folderModel.findWithPermissions(q, user=user, level=AccessType.READ)
        else:
            imageFolders = folderModel.find(q)

        images = []

        for imageFolder in imageFolders:
            qt = {
                'meta.slicerCLIType': 'tag',
                'parentId': imageFolder['_id']
            }
            if user:
                tagFolders = folderModel.findWithPermissions(qt, user=user, level=AccessType.READ)
            else:
                tagFolders = folderModel.find(qt)
            for tagFolder in tagFolders:
                images.append(DockerImageItem(imageFolder, tagFolder, user))
        return images

    @staticmethod
    def removeImages(names, user):
        folderModel = Folder()
        removed = []
        for name in names:
            image, tag = _split(name)
            q = {
                'meta.slicerCLIType': 'image',
                'name': image
            }
            imageFolder = folderModel.findOne(q, user=user, level=AccessType.READ)
            if not imageFolder:
                continue
            qt = {
                'meta.slicerCLIType': 'tag',
                'parentId': imageFolder['_id'],
                'name': tag
            }
            tagFolder = folderModel.findOne(qt, user=user, level=AccessType.WRITE)
            if not tagFolder:
                continue
            folderModel.remove(tagFolder)
            removed.append(name)

            if folderModel.hasAccess(imageFolder, user, AccessType.WRITE) and \
               folderModel.countFolders(imageFolder) == 0:
                # clean also empty image folders
                folderModel.remove(imageFolder)

        return removed

    @staticmethod
    def _create(name, docker_image, user, baseFolder):
        folderModel = Folder()
        fileModel = File()

        imageName, tagName = _split(name)

        image = folderModel.createFolder(baseFolder, imageName,
                                         'Slicer CLI generated docker image folder',
                                         creator=user, reuseExisting=True)
        folderModel.setMetadata(image, dict(slicerCLIType='image'))

        fileModel.createLinkFile('Docker Hub', image, 'folder',
                                 'https://hub.docker.com/r/%s' % imageName,
                                 user, reuseExisting=True)

        tag = folderModel.createFolder(image, tagName,
                                       'Slicer CLI generated docker image tag folder',
                                       creator=user, reuseExisting=True)

        # add docker image labels as meta data
        labels = docker_image.labels.copy()
        if 'description' in labels:
            tag['description'] = labels['description']
            del labels['description']
        labels = {k.replace('.', '_'): v for k, v in labels.items()}
        if 'Author' in docker_image.attrs:
            labels['author'] = docker_image.attrs['Author']

        digest = None
        if docker_image.attrs.get('RepoDigests', []):
            digest = docker_image.attrs['RepoDigests'][0]

        labels['digest'] = digest
        folderModel.setMetadata(tag, labels)

        folderModel.setMetadata(tag, dict(slicerCLIType='tag'))

        return DockerImageItem(image, tag, user)

    @staticmethod
    def _syncItems(image, cli_dict, user):
        folderModel = Folder()
        itemModel = Item()

        children = folderModel.childItems(image.tagFolder, filters={'meta.slicerCLIType': 'task'})
        existingItems = {item['name']: item for item in children}

        for cli, desc in cli_dict.items():
            item = itemModel.createItem(cli, user, image.tagFolder,
                                        'Slicer CLI generated CLI command item',
                                        reuseExisting=True)
            meta_data = dict(slicerCLIType='task', type=desc.get('type', 'Unknown'))

            # copy some things from the image to be independent
            meta_data['image'] = image.name
            meta_data['digest'] = image.digest if image.name != image.digest else None
            if desc.get('docker-params'):
                meta_data['docker-params'] = desc['docker-params']

            desc_type = desc.get('desc-type', 'xml')

            if desc_type == 'xml':
                meta_data.update(parse_xml_desc(item, desc, user))
            elif desc_type == 'yaml':
                meta_data.update(parse_yaml_desc(item, desc, user))
            elif desc_type == 'json':
                meta_data.update(parse_json_desc(item, desc, user))

            itemModel.setMetadata(item, meta_data)

            if cli in existingItems:
                del existingItems[cli]

        # delete superfluous items
        for item in existingItems.values():
            itemModel.remove(item)

    @staticmethod
    def saveImage(name, cli_dict, docker_image, user, baseFolder):
        """
        :param baseFolder
        :type Folder
        """
        image = DockerImageItem._create(name, docker_image, user, baseFolder)
        DockerImageItem._syncItems(image, cli_dict, user)

        return image

    @staticmethod
    def prepare():
        Item().ensureIndex(['meta.slicerCLIType', {'sparse': True}])
