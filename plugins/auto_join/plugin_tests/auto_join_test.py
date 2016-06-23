from tests import base


def setUpModule():
    base.enabledPlugins.append('auto_join')
    base.startServer()


def tearDownModule():
    base.stopServer()


class AutoJoinTest(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)
