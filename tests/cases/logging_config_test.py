#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#############################################################################

# import cherrypy
# import logging
import os
import shutil
import six
import sys
import tempfile

from .. import base
import girder
from girder import logger, logprint
from girder.utility import config


def setUpModule():
    logRoot = tempfile.mkdtemp()
    infoFile = os.path.join(logRoot, 'config_info.log')
    errorFile = os.path.join(logRoot, 'config_error.log')
    cfg = config.getConfig()
    cfg['logging'] = {
        'log_root': logRoot,
        'info_log_file': infoFile,
        'error_log_file': errorFile,
        'original_error_log_file': errorFile,  # so we can change error_log_file
    }
    cfg = config.getConfig()
    base.startServer()


def tearDownModule():
    cfg = config.getConfig()
    logRoot = cfg['logging']['log_root']
    base.stopServer()
    shutil.rmtree(logRoot)


class ConfigLoggingTestCase(base.TestCase):
    """
    Contains tests of configured logging.
    """

    def setUp(self):
        base.TestCase.setUp(self)

        user = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        }
        self.admin = self.model('user').createUser(**user)
        self.infoMessage = 'Log info message'
        self.errorMessage = 'Log error message'

    def configureLogging(self, logConfig={}, oneFile=False):
        cfg = config.getConfig()
        if oneFile:
            cfg['logging']['error_log_file'] = cfg['logging']['info_log_file']
        else:
            cfg['logging']['error_log_file'] = cfg['logging']['original_error_log_file']
        self.infoFile = cfg['logging']['info_log_file']
        self.errorFile = cfg['logging']['error_log_file']
        if os.path.exists(self.infoFile):
            os.unlink(self.infoFile)
        if os.path.exists(self.errorFile):
            os.unlink(self.errorFile)
        cfg['logging'].update(logConfig)
        cfg = config.getConfig()
        girder.logger = girder._setupLogger()

    def testFileRotation(self):
        self.configureLogging({
            'log_access': ['screen', 'info'],
            'log_quiet': True,
            'log_max_size': '1 kb',
            'log_backup_count': 2,
            'log_level': 'DEBUG',
        })

        logger.info(self.infoMessage)
        logger.error(self.errorMessage)
        infoSize = os.path.getsize(self.infoFile)
        errorSize = os.path.getsize(self.errorFile)
        self.assertFalse(os.path.exists(self.infoFile + '.1'))
        self.assertFalse(os.path.exists(self.errorFile + '.1'))
        logger.info(self.infoMessage)
        logger.error(self.errorMessage)
        newInfoSize = os.path.getsize(self.infoFile)
        newErrorSize = os.path.getsize(self.errorFile)
        deltaInfo = newInfoSize - infoSize
        deltaError = newErrorSize - errorSize
        self.assertGreater(deltaInfo, len(self.infoMessage))
        self.assertGreater(deltaError, len(self.errorMessage))
        while newInfoSize < 1024 * 1.5:
            logger.info(self.infoMessage)
            newInfoSize += deltaInfo
        while newErrorSize < 1024 * 1.5:
            logger.error(self.errorMessage)
            newErrorSize += deltaError
        self.assertTrue(os.path.exists(self.infoFile + '.1'))
        self.assertTrue(os.path.exists(self.errorFile + '.1'))
        self.assertFalse(os.path.exists(self.infoFile + '.2'))
        self.assertFalse(os.path.exists(self.errorFile + '.2'))
        while newInfoSize < 1024 * 3.5:
            logger.info(self.infoMessage)
            newInfoSize += deltaInfo
        while newErrorSize < 1024 * 3.5:
            logger.error(self.errorMessage)
            newErrorSize += deltaError
        self.assertTrue(os.path.exists(self.infoFile + '.1'))
        self.assertTrue(os.path.exists(self.errorFile + '.1'))
        self.assertTrue(os.path.exists(self.infoFile + '.2'))
        self.assertTrue(os.path.exists(self.errorFile + '.2'))
        self.assertFalse(os.path.exists(self.infoFile + '.3'))
        self.assertFalse(os.path.exists(self.errorFile + '.3'))

    def testCaptureStdoutAndStderr(self):
        self.configureLogging()

        infoSize1 = os.path.getsize(self.infoFile)
        errorSize1 = os.path.getsize(self.errorFile)
        print(self.infoMessage)
        infoSize2 = os.path.getsize(self.infoFile)
        errorSize2 = os.path.getsize(self.errorFile)
        self.assertGreater(infoSize2, infoSize1)
        self.assertEqual(errorSize2, errorSize1)
        six.print_(self.errorMessage, file=sys.stderr, flush=True)
        infoSize3 = os.path.getsize(self.infoFile)
        errorSize3 = os.path.getsize(self.errorFile)
        self.assertEqual(infoSize3, infoSize2)
        self.assertGreater(errorSize3, errorSize2)

    def testOneFile(self):
        self.configureLogging({'log_max_info_level': 'CRITICAL'}, oneFile=True)

        logger.info(self.infoMessage)
        infoSize = os.path.getsize(self.infoFile)
        errorSize = os.path.getsize(self.errorFile)
        self.assertEqual(infoSize, errorSize)
        logger.error(self.errorMessage)
        newInfoSize = os.path.getsize(self.infoFile)
        newErrorSize = os.path.getsize(self.errorFile)
        self.assertEqual(newInfoSize, newErrorSize)
        self.assertGreater(newInfoSize, infoSize)

    def testInfoMaxLevel(self):
        self.configureLogging({'log_max_info_level': 'CRITICAL'})

        infoSize1 = os.path.getsize(self.infoFile)
        errorSize1 = os.path.getsize(self.errorFile)
        logger.info(self.infoMessage)
        infoSize2 = os.path.getsize(self.infoFile)
        errorSize2 = os.path.getsize(self.errorFile)
        self.assertGreater(infoSize2, infoSize1)
        self.assertEqual(errorSize2, errorSize1)
        logger.error(self.errorMessage)
        infoSize3 = os.path.getsize(self.infoFile)
        errorSize3 = os.path.getsize(self.errorFile)
        self.assertGreater(infoSize3, infoSize2)
        self.assertGreater(errorSize3, errorSize2)

    def testLogPrint(self):
        self.configureLogging({'log_max_info_level': 'INFO'})

        infoSize1 = os.path.getsize(self.infoFile)
        errorSize1 = os.path.getsize(self.errorFile)
        logprint.info(self.infoMessage)
        infoSize2 = os.path.getsize(self.infoFile)
        errorSize2 = os.path.getsize(self.errorFile)
        self.assertGreater(infoSize2, infoSize1)
        self.assertEqual(errorSize2, errorSize1)
        logprint.error(self.errorMessage)
        infoSize3 = os.path.getsize(self.infoFile)
        errorSize3 = os.path.getsize(self.errorFile)
        # logprint sends to stdout, which we capture except when sent via
        # logprint, so we shouldn't see any additional data on the info log.
        self.assertEqual(infoSize3, infoSize2)
        self.assertGreater(errorSize3, errorSize2)
