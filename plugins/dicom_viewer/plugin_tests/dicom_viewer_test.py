import os
import json
import six

from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.upload import Upload
from girder.models.user import User
import pydicom
from tests import base

from girder_dicom_viewer import _removeUniqueMetadata, _extractFileData
from girder_dicom_viewer.event_helper import _EventHelper


def setUpModule():
    base.enabledPlugins.append('dicom_viewer')
    base.startServer()
    global _removeUniqueMetadata
    global _extractFileData


def tearDownModule():
    base.stopServer()


class DicomViewerTest(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)
        self.dataDir = os.path.join(
            os.environ['GIRDER_TEST_DATA_PREFIX'], 'plugins', 'dicom_viewer')

        self.users = [User().createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@u.com' % num)
            for num in [0, 1]]

    def testRemoveUniqueMetadata(self):
        dicomMeta = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3',
            'key4': 35,
            'key5': 54,
            'key6': 'commonVal',
            'uniqueKey1': 'commonVal'
        }
        additionalMeta = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3',
            'key4': 35,
            'key5': 54,
            'key6': 'uniqueVal',
            'uniqueKey2': 'commonVal',

        }
        commonMeta = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3',
            'key4': 35,
            'key5': 54
        }
        self.assertEqual(_removeUniqueMetadata(dicomMeta, additionalMeta), commonMeta)

    def testExtractFileData(self):
        dicomFile = {
            '_id': '599c4cf3c9c5cb11f1ff5d97',
            'assetstoreId': '599c4a19c9c5cb11f1ff5d32',
            'creatorId': '5984b9fec9c5cb370447068c',
            'exts': ['dcm'],
            'itemId': '599c4cf3c9c5cb11f1ff5d96',
            'mimeType': 'application/dicom',
            'name': '000000.dcm',
            'size': 133356
        }
        dicomMeta = {
            'SeriesNumber': 1,
            'InstanceNumber': 1,
            'SliceLocation': 0
        }
        result = {
            '_id': '599c4cf3c9c5cb11f1ff5d97',
            'name': '000000.dcm',
            'dicom': {
                'SeriesNumber': 1,
                'InstanceNumber': 1,
                'SliceLocation': 0
            }
        }
        self.assertEqual(_extractFileData(dicomFile, dicomMeta), result)

    def testFileProcessHandler(self):
        admin, user = self.users

        # Create a collection, folder, and item
        collection = Collection().createCollection('collection1', admin, public=True)
        folder = Folder().createFolder(collection, 'folder1', parentType='collection', public=True)
        item = Item().createItem('item1', admin, folder)

        # Upload non-DICOM files
        self._uploadNonDicomFiles(item, admin)
        nonDicomItem = Item().load(item['_id'], force=True)
        self.assertIsNone(nonDicomItem.get('dicom'))

        # Upload DICOM files
        self._uploadDicomFiles(item, admin)

        # Check if the 'dicomItem' is well processed
        dicomItem = Item().load(item['_id'], force=True)
        self.assertIn('dicom', dicomItem)
        self.assertHasKeys(dicomItem['dicom'], ['meta', 'files'])

        # Check if the files list contain the good keys and all the file are well sorted
        for i in range(0, 4):
            self.assertTrue('_id' in dicomItem['dicom']['files'][i])
            self.assertTrue('name' in dicomItem['dicom']['files'][i])
            self.assertEqual(dicomItem['dicom']['files'][i]['name'], 'dicomFile{}.dcm'.format(i))
            self.assertTrue('SeriesNumber' in dicomItem['dicom']['files'][i]['dicom'])
            self.assertTrue('InstanceNumber' in dicomItem['dicom']['files'][i]['dicom'])
            self.assertTrue('SliceLocation' in dicomItem['dicom']['files'][i]['dicom'])

        # Check the common metadata
        self.assertIsNotNone(dicomItem['dicom']['meta'])

    def testMakeDicomItem(self):
        admin, user = self.users

        # create a collection, folder, and item
        collection = Collection().createCollection('collection2', admin, public=True)
        folder = Folder().createFolder(collection, 'folder2', parentType='collection', public=True)
        item = Item().createItem('item2', admin, folder)

        # Upload files
        self._uploadDicomFiles(item, admin)

        # Check the endpoint 'parseDicom' for an admin user
        dicomItem = Item().load(item['_id'], force=True)
        dicomItem = self._purgeDicomItem(dicomItem)
        path = '/item/%s/parseDicom' % dicomItem.get('_id')
        resp = self.request(path=path, method='POST', user=admin)
        self.assertStatusOk(resp)
        dicomItem = Item().load(item['_id'], force=True)
        self.assertIn('dicom', dicomItem)
        self.assertHasKeys(dicomItem['dicom'], ['meta', 'files'])

        # Check the endpoint 'parseDicom' for an non admin user
        dicomItem = Item().load(item['_id'], force=True)
        dicomItem = self._purgeDicomItem(dicomItem)
        path = '/item/%s/parseDicom' % dicomItem.get('_id')
        resp = self.request(path=path, method='POST', user=user)
        self.assertStatus(resp, 403)

    def _uploadNonDicomFiles(self, item, user):
        # Upload a fake file to check that the item is not traited
        nonDicomContent = b'hello world\n'

        ndcmFile = Upload().uploadFromFile(
            obj=six.BytesIO(nonDicomContent),
            size=len(nonDicomContent),
            name='nonDicom.txt',
            parentType='item',
            parent=item,
            mimeType='text/plain',
            user=user
        )
        self.assertIsNotNone(ndcmFile)

    def _uploadDicomFiles(self, item, user):
        # Upload the files in the reverse order to check if they're well sorted
        for i in [1, 3, 0, 2]:
            file = os.path.join(self.dataDir, '00000%i.dcm' % i)
            with open(file, 'rb') as fp, _EventHelper('dicom_viewer.upload.success') as helper:
                dcmFile = Upload().uploadFromFile(
                    obj=fp,
                    size=os.path.getsize(file),
                    name='dicomFile{}.dcm'.format(i),
                    parentType='item',
                    parent=item,
                    mimeType='application/dicom',
                    user=user
                )
                self.assertIsNotNone(dcmFile)
                # Wait for handler success event
                handled = helper.wait()
                self.assertTrue(handled)

    def _purgeDicomItem(self, item):
        item.pop('dicom')
        return item

    def testSearchForDicomItem(self):
        admin, user = self.users

        # Create a collection, folder, and item
        collection = Collection().createCollection('collection3', admin, public=True)
        folder = Folder().createFolder(collection, 'folder3', parentType='collection', public=True)
        item = Item().createItem('item3', admin, folder)

        # Upload files
        self._uploadDicomFiles(item, admin)

        # Search for DICOM item with 'brain research' as common key/value
        resp = self.request(path='/resource/search', params={
            'q': 'brain research',
            'mode': 'dicom',
            'types': json.dumps(['item'])
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['item']), 1)
        self.assertEqual(resp.json['item'][0]['name'], 'item3')

        # Search for DICOM item with substring 'in resea' as common key/value
        resp = self.request(path='/resource/search', params={
            'q': 'in resea',
            'mode': 'dicom',
            'types': json.dumps(['item'])
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['item']), 1)
        self.assertEqual(resp.json['item'][0]['name'], 'item3')

        # TODO: Add test to search for a private DICOM item with an other user
        # this test should not found anything

    def testDicomWithIOError(self):
        # One of the test files in the pydicom module will throw an IOError
        # when parsing metadata.  We should work around that and still be able
        # to import the file
        samplePath = os.path.join(os.path.dirname(os.path.abspath(
            pydicom.__file__)), 'data', 'test_files', 'CT_small.dcm')
        admin, user = self.users
        # Create a collection, folder, and item
        collection = Collection().createCollection('collection4', admin, public=True)
        folder = Folder().createFolder(collection, 'folder4', parentType='collection', public=True)
        item = Item().createItem('item4', admin, folder)
        # Upload this dicom file
        with open(samplePath, 'rb') as fp, _EventHelper('dicom_viewer.upload.success') as helper:
            dcmFile = Upload().uploadFromFile(
                obj=fp,
                size=os.path.getsize(samplePath),
                name=os.path.basename(samplePath),
                parentType='item',
                parent=item,
                mimeType='application/dicom',
                user=user
            )
            self.assertIsNotNone(dcmFile)
            # Wait for handler success event
            handled = helper.wait()
            self.assertTrue(handled)
        # Check if the 'dicomItem' is well processed
        dicomItem = Item().load(item['_id'], force=True)
        self.assertIn('dicom', dicomItem)
        self.assertHasKeys(dicomItem['dicom'], ['meta', 'files'])

    def testDicomWithBinaryValues(self):
        # One of the test files in the pydicom module will throw an IOError
        # when parsing metadata.  We should work around that and still be able
        # to import the file
        samplePath = os.path.join(os.path.dirname(os.path.abspath(
            pydicom.__file__)), 'data', 'test_files', 'OBXXXX1A.dcm')
        admin, user = self.users
        # Create a collection, folder, and item
        collection = Collection().createCollection('collection5', admin, public=True)
        folder = Folder().createFolder(collection, 'folder5', parentType='collection', public=True)
        item = Item().createItem('item5', admin, folder)
        # Upload this dicom file
        with open(samplePath, 'rb') as fp, _EventHelper('dicom_viewer.upload.success') as helper:
            dcmFile = Upload().uploadFromFile(
                obj=fp,
                size=os.path.getsize(samplePath),
                name=os.path.basename(samplePath),
                parentType='item',
                parent=item,
                mimeType='application/dicom',
                user=user
            )
            self.assertIsNotNone(dcmFile)
            # Wait for handler success event
            handled = helper.wait()
            self.assertTrue(handled)
        # Check if the 'dicomItem' is well processed
        dicomItem = Item().load(item['_id'], force=True)
        self.assertIn('dicom', dicomItem)
        self.assertHasKeys(dicomItem['dicom'], ['meta', 'files'])
