#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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
import six
import subprocess
import sys
import time

from girder import config
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, RestException
from girder.constants import ROOT_DIR
from girder.utility.progress import ProgressContext
from . import base
from six.moves import range

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_PORT', '30001')
config.loadConfig()  # Reload config to pick up correct port
testServer = None

reload(sys)
sys.setdefaultencoding('utf-8')


def setUpModule():
    global testServer
    mockS3 = False
    if 's3' in os.environ['ASSETSTORE_TYPE']:
        mockS3 = True

    pluginDirs = os.environ.get('PLUGIN_DIRS', '')

    if pluginDirs:
        curConfig = config.getConfig()
        curConfig['plugins'] = {'plugin_directory': pluginDirs}

    plugins = os.environ.get('ENABLED_PLUGINS', '')
    if plugins:
        base.enabledPlugins.extend(plugins.split())
    testServer = base.startServer(False, mockS3=mockS3)


def tearDownModule():
    base.stopServer()


class WebClientTestEndpoints(Resource):
    def __init__(self):
        super(WebClientTestEndpoints, self).__init__()
        self.route('GET', ('progress', ), self.testProgress)
        self.route('PUT', ('progress', 'stop'), self.testProgressStop)
        self.route('POST', ('file', ), self.uploadFile)
        self.stop = False

    @access.token
    @describeRoute(
        Description('Test progress contexts from the web')
        .param('test', 'Name of test to run.  These include "success" and '
               '"failure".', required=False)
        .param('duration', 'Duration of the test in seconds', required=False,
               dataType='int')
    )
    def testProgress(self, params):
        test = params.get('test', 'success')
        duration = int(params.get('duration', 10))
        startTime = time.time()
        with ProgressContext(True, user=self.getCurrentUser(),
                             title='Progress Test', message='Progress Message',
                             total=duration) as ctx:
            for current in range(duration):
                if self.stop:
                    break
                ctx.update(current=current)
                wait = startTime + current + 1 - time.time()
                if wait > 0:
                    time.sleep(wait)
            if test == 'error':
                raise RestException('Progress error test.')

    @access.token
    @describeRoute(
        Description('Halt all progress tests')
    )
    def testProgressStop(self, params):
        self.stop = True

    @access.user
    @describeRoute(None)
    def uploadFile(self, params):
        """
        Providing this works around a limitation in phantom that makes us
        unable to upload binary files, or at least ones that contain certain
        byte values. The path parameter should be provided relative to the
        root directory of the repository.
        """
        self.requireParams(('folderId', 'path'), params)

        path = os.path.join(ROOT_DIR, params['path'])
        name = os.path.basename(path)
        folder = self.model('folder').load(params['folderId'], force=True)

        upload = self.model('upload').createUpload(
            user=self.getCurrentUser(), name=name, parentType='folder',
            parent=folder, size=os.path.getsize(path))

        with open(path, 'rb') as fd:
            file = self.model('upload').handleChunk(upload, fd)

        return file


class WebClientTestCase(base.TestCase):
    def setUp(self):
        self.specFile = os.environ['SPEC_FILE']
        self.coverageFile = os.environ.get('COVERAGE_FILE', '')
        assetstoreType = os.environ['ASSETSTORE_TYPE']
        self.webSecurity = os.environ.get('WEB_SECURITY', 'true')
        if self.webSecurity != 'false':
            self.webSecurity = 'true'
        base.TestCase.setUp(self, assetstoreType)
        # One of the web client tests uses this db, so make sure it is cleared
        # ahead of time.  This still allows tests to be run in parallel, since
        # nothing should be stored in this db
        base.dropGridFSDatabase('girder_webclient_gridfs')

        testServer.root.api.v1.webclienttest = WebClientTestEndpoints()

    def testWebClientSpec(self):
        baseUrl = '/static/built/testing/testEnv.html'
        if os.environ.get('BASEURL', ''):
            baseUrl = os.environ['BASEURL']

        cmd = (
            os.path.join(
                ROOT_DIR, 'node_modules', 'phantomjs', 'bin', 'phantomjs'),
            '--web-security=%s' % self.webSecurity,
            os.path.join(ROOT_DIR, 'clients', 'web', 'test', 'specRunner.js'),
            'http://localhost:%s%s' % (os.environ['GIRDER_PORT'], baseUrl),
            self.specFile,
            self.coverageFile,
            os.environ.get('JASMINE_TIMEOUT', '')
        )

        # phantomjs occasionally fails to load javascript files.  This appears
        # to be a known issue: https://github.com/ariya/phantomjs/issues/10652.
        # Retry several times if it looks like this has occurred.
        retry_count = os.environ.get('PHANTOMJS_RETRY', 5)
        for tries in range(int(retry_count)):
            retry = False
            task = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            hasJasmine = False
            jasmineFinished = False
            for line in iter(task.stdout.readline, b''):
                if isinstance(line, six.binary_type):
                    line = line.decode('utf8')
                if ('PHANTOM_TIMEOUT' in line or
                        'error loading source script' in line):
                    task.kill()
                    retry = True
                elif '__FETCHEMAIL__' in line:
                    base.mockSmtp.waitForMail()
                    msg = base.mockSmtp.getMail(parse=True)
                    open('phantom_temp_%s.tmp' % os.environ['GIRDER_PORT'],
                         'wb').write(msg.get_payload(decode=True))
                    continue  # we don't want to print this
                if 'Jasmine' in line:
                    hasJasmine = True
                if 'Testing Finished' in line:
                    jasmineFinished = True
                sys.stdout.write(line.encode('utf8', 'replace'))
                sys.stdout.flush()
            returncode = task.wait()
            if not retry and hasJasmine and jasmineFinished:
                break
            if not hasJasmine:
                time.sleep(1)
            sys.stderr.write('Retrying test\n')
            # If we are retrying, we need to reset the whole test, as the
            # databases and other resources are in an unknown state
            self.tearDown()
            self.setUp()

        self.assertEqual(returncode, 0)
