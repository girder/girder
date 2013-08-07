from .. import base

def setUpModule():
    base.startServer()

def tearDownModule():
    base.stopServer()

class FolderTestCase(base.TestCase):
    pass
