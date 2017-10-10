import os
import time

from tests import base
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.upload import Upload
from girder.models.user import User


def setUpModule():
    base.enabledPlugins.append('dicom_viewer')
    base.startServer()


def tearDownModule():
    base.stopServer()


class DicomViewerTest(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        self.users = [User().createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@u.com' % num)
            for num in [0, 1]]

    def testDicomViewer(self):
        admin, user = self.users

        # create a collection, folder, and item
        collection = Collection().createCollection('collection', admin, public=True)
        folder = Folder().createFolder(collection, 'folder', parentType='collection', public=True)
        item = Item().createItem('item', admin, folder)

        # test initial values
        path = '/item/%s/dicom' % item.get('_id')
        resp = self.request(path=path, user=admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        path = os.path.join(os.path.split(__file__)[0], 'test.dcm')
        with open(path, 'rb') as fp:
            Upload().uploadFromFile(fp, 25640, 'test.dcm', 'item', item, admin)

        path = os.path.join(os.path.split(__file__)[0], 'not-dicom.dcm')
        with open(path, 'rb') as fp:
            Upload().uploadFromFile(fp, 7590, 'not-dicom.dcm', 'item', item, admin)

        # test dicom endpoint
        start = time.time()
        while True:
            try:
                path = '/item/%s/dicom' % item.get('_id')
                resp = self.request(path=path, user=admin)
                break
            except AssertionError:
                if time.time() - start > 15:
                    raise
                time.sleep(0.5)

        self.assertStatusOk(resp)

        # one dicom file found
        files = resp.json
        self.assertEqual(len(files), 1)

        # dicom tags present
        file = files[0]
        dicom = file['dicom']
        self.assertEqual(bool(dicom), True)

        # dicom tags correct
        self.assertEqual(dicom['Rows'], 80)
        self.assertEqual(dicom['Columns'], 150)

        # test filters
        path = '/item/%s/dicom' % item.get('_id')
        resp = self.request(path=path, user=admin, params=dict(filters='Rows'))
        self.assertStatusOk(resp)
        dicom = resp.json[0]['dicom']
        self.assertEqual(dicom['Rows'], 80)
        self.assertEqual(dicom.get('Columns'), None)

        # test non-admin force
        path = '/item/%s/dicom' % item.get('_id')
        resp = self.request(path=path, user=user, params=dict(force=True))
        self.assertStatus(resp, 403)
