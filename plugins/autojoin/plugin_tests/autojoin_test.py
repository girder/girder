from tests import base


def setUpModule():
    base.enabledPlugins.append('autojoin')
    base.startServer()


def tearDownModule():
    base.stopServer()


class AutoJoinTest(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)
