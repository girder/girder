import json

from tests import base
from girder.constants import AccessType, SortDir
from girder.exceptions import ValidationException
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.user import User


def setUpModule():
    base.enabledPlugins.append('virtual_folders')
    base.startServer()


def tearDownModule():
    base.stopServer()


class VirtualFoldersTestCase(base.TestCase):
    def setUp(self):
        super().setUp()

        self.admin = User().createUser(
            email='admin@admin.com', login='admin', lastName='admin', firstName='admin',
            password='passwd', admin=True)
        self.user = User().createUser(
            email='user@girder.test', login='user', lastName='u', firstName='u', password='passwd')

        self.f1 = Folder().createFolder(self.admin, 'f1', creator=self.admin, parentType='user')
        self.f2 = Folder().createFolder(self.admin, 'f2', creator=self.admin, parentType='user')
        self.virtual = Folder().createFolder(self.user, 'v', creator=self.user, parentType='user')
        self.virtual['isVirtual'] = True

    def testVirtualQuery(self):
        for i in range(10):
            item = Item().createItem(str(i), creator=self.admin, folder=(self.f1, self.f2)[i % 2])
            Item().setMetadata(item, {
                'someVal': i
            })

        self.virtual['virtualItemsQuery'] = json.dumps({
            'meta.someVal': {
                '$gt': 5
            }
        })
        self.virtual = Folder().save(self.virtual)

        def listItems():
            resp = self.request('/item', user=self.user, params={
                'folderId': self.virtual['_id']
            })
            self.assertStatusOk(resp)
            return resp.json

        def getDetails():
            resp = self.request('/folder/%s/details' % self.virtual['_id'], user=self.user)
            self.assertStatusOk(resp)
            details = resp.json
            self.assertEqual(details['nFolders'], 0)
            return details['nItems']

        self.assertEqual(listItems(), [])

        # Grant permission on the first folder
        Folder().setUserAccess(self.f1, self.user, AccessType.READ, save=True)
        self.assertEqual([i['name'] for i in listItems()], ['6', '8'])
        self.assertEqual(getDetails(), 2)

        # Grant permission on the second folder
        Folder().setUserAccess(self.f2, self.user, AccessType.READ, save=True)
        self.assertEqual([i['name'] for i in listItems()], ['6', '7', '8', '9'])
        self.assertEqual(getDetails(), 4)

        # item/position/:id should work
        items = listItems()
        resp = self.request('/item/%s/position' % items[2]['_id'], user=self.user, params={
            'folderId': self.virtual['_id']})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, 2)

        # Add a custom sort
        self.virtual['virtualItemsSort'] = json.dumps([('meta.someVal', SortDir.DESCENDING)])
        self.virtual = Folder().save(self.virtual)
        self.assertEqual([i['name'] for i in listItems()], ['9', '8', '7', '6'])

        # Using childItems on a vfolder should not yield any results
        self.assertEqual(list(Folder().childItems(self.virtual)), [])

    def testVirtualFolderValidation(self):
        # Can't make folder virtual if it has children
        subfolder = Folder().createFolder(self.f1, 'sub', creator=self.admin)
        self.f1['isVirtual'] = True

        with self.assertRaisesRegex(
                ValidationException, 'Virtual folders may not contain child folders.'):
            Folder().save(self.f1)

        Folder().remove(subfolder)
        item = Item().createItem('i', creator=self.admin, folder=self.f1)

        with self.assertRaisesRegex(
                ValidationException, 'Virtual folders may not contain child items.'):
            Folder().save(self.f1)

        Item().remove(item)
        Folder().save(self.f1)

        # Can't make subfolders or items under a virtual folder
        with self.assertRaisesRegex(
                ValidationException, 'You may not place items under a virtual folder.'):
            Item().createItem('i', creator=self.admin, folder=self.f1)

        with self.assertRaisesRegex(
                ValidationException, 'You may not place folders under a virtual folder.'):
            Folder().createFolder(self.f1, 'f', creator=self.admin)

        # Can't move an item under a virtual folder
        item = Item().createItem('i', creator=self.admin, folder=self.f2)
        with self.assertRaisesRegex(
                ValidationException, 'You may not place items under a virtual folder.'):
            Item().move(item, self.f1)

        # Ensure JSON for query
        self.f1['virtualItemsQuery'] = 'not JSON'
        with self.assertRaisesRegex(
                ValidationException, 'The virtual items query must be valid JSON.'):
            Folder().save(self.f1)

        del self.f1['virtualItemsQuery']
        self.f1['virtualItemsSort'] = 'not JSON'
        with self.assertRaisesRegex(
                ValidationException, 'The virtual items sort must be valid JSON.'):
            Folder().save(self.f1)

    def testRestEndpoint(self):
        def updateFolder(user):
            return self.request('/folder/%s' % self.f1['_id'], method='PUT', params={
                'isVirtual': True,
                'virtualItemsQuery': json.dumps({'foo': 'bar'}),
                'virtualItemsSort': json.dumps([('meta.someVal', SortDir.DESCENDING)])
            }, user=user)

        Folder().setUserAccess(self.f1, self.user, level=AccessType.ADMIN, save=True)

        resp = updateFolder(self.user)
        self.assertStatus(resp, 403)
        self.assertEqual(resp.json['message'], 'Must be admin to setup virtual folders.')
        f1 = Folder().load(self.f1['_id'], force=True)
        self.assertNotIn('isVirtual', f1)
        self.assertNotIn('virtualItemsQuery', f1)
        self.assertNotIn('virtualItemsSort', f1)

        resp = updateFolder(self.admin)
        self.assertStatusOk(resp)
        self.assertTrue(Folder().load(self.f1['_id'], force=True)['isVirtual'])
