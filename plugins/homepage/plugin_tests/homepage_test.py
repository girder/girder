# -*- coding: utf-8 -*-
from girder.models.setting import Setting
from tests import base


def setUpModule():
    base.enabledPlugins.append('homepage')
    base.startServer()


def tearDownModule():
    base.stopServer()


class HomepageTest(base.TestCase):

    def testGetMarkdown(self):
        key = 'homepage.markdown'

        # test without set
        resp = self.request('/homepage')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[key], '')

        # set markdown
        Setting().set(key, 'foo')

        # verify we can get the markdown without being authenticated
        resp = self.request('/homepage')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[key], 'foo')
