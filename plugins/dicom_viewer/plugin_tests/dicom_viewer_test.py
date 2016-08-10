from tests import base
import os


def setUpModule():
    base.enabledPlugins.append('dicom_viewer')
    base.startServer()


def tearDownModule():
    base.stopServer()


class DicomViewerTest(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        self.users = [self.model('user').createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@u.com' % num)
            for num in [0, 1]]

    def testDicomViewer(self):
        admin, user = self.users

        # create a collection, folder, and item
        collection = self.model('collection').createCollection(
            'collection', admin, public=True)
        folder = self.model('folder').createFolder(
            collection, 'folder', parentType='collection', public=True)
        item = self.model('item').createItem('item', admin, folder)

        # test initial values
        path = '/item/%s/dicom' % item.get('_id')
        resp = self.request(path=path, user=admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        path = os.path.join(os.path.split(__file__)[0], 'test.dcm')
        with open(path, 'rb') as fp:
            fp.seek(0, 2)
            size = fp.tell()
            fp.seek(0)
            self.model('upload').uploadFromFile(
                fp, size, 'test.dcm', 'item', item, admin)

        # test dicom endpoint
        path = '/item/%s/dicom' % item.get('_id')
        resp = self.request(path=path, user=admin)
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
