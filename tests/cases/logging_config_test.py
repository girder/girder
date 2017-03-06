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
import tempfile

import girder
from .. import base
from girder.utility import config


def setUpModule():
    logRoot = tempfile.mkdtemp()
    infoFile = os.path.join(logRoot, 'config_info.log')
    errorFile = os.path.join(logRoot, 'config_error.log')
    cfg = config.getConfig()
    cfg['logging'] = {
        'log_root': logRoot,
        'info_log_file': infoFile,
        'error_log_file': errorFile
    }
    cfg = config.getConfig()


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
        cfg = config.getConfig()
        cfg['logging'].update({
            'log_access': ['screen', 'info'],
            'log_quiet': True,
            'log_max_size': '1 kb',
            'log_backup_count': 2,
            'log_level': 'DEBUG',
        })
        self.infoFile = cfg['logging']['info_log_file']
        self.errorFile = cfg['logging']['error_log_file']
        girder.logger = girder._setupLogger()
        base.startServer()
        base.TestCase.setUp(self)

        user = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        }
        self.admin = self.model('user').createUser(**user)

    def testRotation(self):
        from girder import logger

        infoMessage = 'Log info message'
        errorMessage = 'Log info message'
        logger.info(infoMessage)
        logger.error(errorMessage)
        infoSize = os.path.getsize(self.infoFile)
        errorSize = os.path.getsize(self.errorFile)
        self.assertFalse(os.path.exists(self.infoFile + '.1'))
        self.assertFalse(os.path.exists(self.errorFile + '.1'))
        logger.info(infoMessage)
        logger.error(errorMessage)
        newInfoSize = os.path.getsize(self.infoFile)
        newErrorSize = os.path.getsize(self.errorFile)
        deltaInfo = newInfoSize - infoSize
        deltaError = newErrorSize - errorSize
        self.assertGreater(deltaInfo, len(infoMessage))
        self.assertGreater(deltaError, len(errorMessage))
        while newInfoSize < 1024 * 1.5:
            logger.info(infoMessage)
            newInfoSize += deltaInfo
        while newErrorSize < 1024 * 1.5:
            logger.error(errorMessage)
            newErrorSize += deltaError
        self.assertTrue(os.path.exists(self.infoFile + '.1'))
        self.assertTrue(os.path.exists(self.errorFile + '.1'))
        self.assertFalse(os.path.exists(self.infoFile + '.2'))
        self.assertFalse(os.path.exists(self.errorFile + '.2'))
        while newInfoSize < 1024 * 3.5:
            logger.info(infoMessage)
            newInfoSize += deltaInfo
        while newErrorSize < 1024 * 3.5:
            logger.error(errorMessage)
            newErrorSize += deltaError
        self.assertTrue(os.path.exists(self.infoFile + '.1'))
        self.assertTrue(os.path.exists(self.errorFile + '.1'))
        self.assertTrue(os.path.exists(self.infoFile + '.2'))
        self.assertTrue(os.path.exists(self.errorFile + '.2'))
        self.assertFalse(os.path.exists(self.infoFile + '.3'))
        self.assertFalse(os.path.exists(self.errorFile + '.3'))
