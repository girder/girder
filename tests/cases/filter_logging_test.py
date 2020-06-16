# -*- coding: utf-8 -*-
import cherrypy
import logging
import os
import shutil
import tempfile
import time

from .. import base
from girder.api import filter_logging
from girder.models.user import User
from girder.utility import config


def setUpModule():
    logRoot = tempfile.mkdtemp()
    infoFile = os.path.join(logRoot, 'filter.log')
    cfg = config.getConfig()
    cfg['log.access_file'] = infoFile
    cfg['logging'] = {'log_root': logRoot, 'info_log_file': infoFile}
    base.startServer()


def tearDownModule():
    cfg = config.getConfig()
    logRoot = cfg['logging']['log_root']
    base.stopServer()
    shutil.rmtree(logRoot)


class FilterLoggingTestCase(base.TestCase):
    """
    Contains tests for filtering cherrypy logging.
    """

    def setUp(self):
        super().setUp()

        user = {
            'email': 'good@girder.test',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        }
        self.admin = User().createUser(**user)

    def _checkLogCount(self, numRequests, numLogged, logFile=None, duration=None):
        resp = self.request(path='/system/log', user=self.admin, params={
            'log': 'info', 'bytes': 1
        }, isJson=False)
        self.assertStatusOk(resp)
        for i in range(numRequests):
            if isinstance(duration, list) and i < len(duration):
                time.sleep(duration[i])
            self.request(path='/system/version', method='GET')
            self.assertStatusOk(resp)
        chunkSize = 32768
        resp = self.request(path='/system/log', user=self.admin, params={
            'log': 'info', 'bytes': chunkSize
        }, isJson=False)
        self.assertStatusOk(resp)
        log = self.getBody(resp)
        logEntries = log.split('/api/v1/system/log')[-2].split(
            '/api/v1/system/version')[1:]
        self.assertEqual(len(logEntries), numLogged)

        if logFile:
            with open(logFile) as fptr:
                log = fptr.read()
                logEntries = log.split('/api/v1/system/log')[-2].split(
                    '/api/v1/system/version')[1:]
                self.assertEqual(len(logEntries), numLogged)

    def testFilterFrequency(self):
        self._checkLogCount(1, 1)
        self._checkLogCount(3, 3)

        regex = 'GET (/[^/ ?#]+)*/system/version[/ ?#]'
        # log every third version request
        filter_logging.addLoggingFilter(regex, 3)
        self._checkLogCount(3, 1)
        self._checkLogCount(2, 0)
        self._checkLogCount(1, 1)

        filter_logging.addLoggingFilter(regex, 5)
        self._checkLogCount(10, 2)

        self.assertTrue(filter_logging.removeLoggingFilter(regex))
        self._checkLogCount(2, 2)

        self.assertFalse(filter_logging.removeLoggingFilter(regex))

    def testFilterDuration(self):
        self._checkLogCount(1, 1)
        self._checkLogCount(3, 3)

        regex = 'GET (/[^/ ?#]+)*/system/version[/ ?#]'
        # log every third version request
        filter_logging.addLoggingFilter(regex, duration=3)
        self._checkLogCount(1, 1)
        self._checkLogCount(3, 1, duration=[0, 0, 3.1])
        self._checkLogCount(2, 0, duration=[0, 0])
        self._checkLogCount(1, 1, duration=[3.1])

        self.assertTrue(filter_logging.removeLoggingFilter(regex))
        self._checkLogCount(2, 2, duration=[0, 0])

        self.assertFalse(filter_logging.removeLoggingFilter(regex))

    def testMultipleHandlers(self):
        logRoot = config.getConfig()['logging']['log_root']
        logFile = os.path.join(logRoot, 'second.log')
        fh = logging.FileHandler(logFile)
        cherrypy.log.access_log.addHandler(fh)

        self._checkLogCount(1, 1, logFile)
        self._checkLogCount(3, 3, logFile)

        regex = 'GET (/[^/ ?#]+)*/system/version[/ ?#]'
        # log every third version request
        filter_logging.addLoggingFilter(regex, 3)
        self._checkLogCount(3, 1, logFile)
        self._checkLogCount(2, 0, logFile)
        self._checkLogCount(1, 1, logFile)

        filter_logging.addLoggingFilter(regex, 5)
        self._checkLogCount(10, 2, logFile)

        self.assertTrue(filter_logging.removeLoggingFilter(regex))
        self._checkLogCount(2, 2, logFile)
