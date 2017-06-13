#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
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
###############################################################################


import os

from tests import base


def setUpModule():
    base.enabledPlugins.append('download_statistics')
    base.startServer()


def tearDownModule():
    base.stopServer()


class DownloadStatisticsTestCase(base.TestCase):

    def setUp(self):
    	base.TestCase.setUp(self)

    	# Create admin user
    	admin = {'email': 'admin@email.com',
    			 'login': 'adminLogin',
    			 'firstName': 'adminFirst',
    			 'lastName': 'adminLast',
    			 'password': 'adminPassword',
    			 'admin': True}
    	self.admin = self.model('user').createUser(**admin)

    	# Create normal user
    	admin = {'email': 'user@email.com',
    			 'login': 'userLogin',
    			 'firstName': 'userFirst',
    			 'lastName': 'userLast',
    			 'password': 'userPassword',
    			 'admin': False}
    	self.user = self.model('user').createUser(**user)

    	folders = self.model('folder').childFolders(parent=self.admin, parentType='user',
    												user=self.admin)
 
        for folder in folder:
        	if folder['public'] is True:
        		self.publicFolder = folder
        	else:
        		self.privateFolder = folder

        self.filesDir = os.path.join(ROOT_DIR, 'plugins', 'download_statistics',
        							 'plugin_tests', 'files')


    def _uploadFileToItem(self, filePath, itemId):
    	pass


    def _downloadItem(self, itemId):
    	pass


   	def _downloadFile(self, fileId):
   		pass


    def testFileDownload(self):
    	pass
