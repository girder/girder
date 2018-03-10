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
from girder.api.rest import Resource
from girder.constants import registerAccessFlag, ROOT_DIR
from girder.exceptions import RestException
from girder.models.folder import Folder
from girder.models.upload import Upload
from girder.utility.progress import ProgressContext
from . import base
from six.moves import range

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_PORT', '30001')
config.loadConfig()  # Reload config to pick up correct port
testServer = None


def setUpModule():
    global testServer
    mockS3 = False
    if 's3' in os.environ['ASSETSTORE_TYPE']:
        mockS3 = True

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
        self.route('POST', ('access_flag', ), self.registerAccessFlags)
        self.stop = False

    @access.token
    @describeRoute(
        Description('Test progress contexts from the web')
        .param('test', 'Name of test to run.  These include "success" and '
               '"failure".', required=False)
        .param('duration', 'Duration of the test in seconds', required=False,
               dataType='int')
        .param('resourceId', 'Resource ID associated with the progress notification.',
               required=False)
        .param('resourceName', 'Type of resource associated with the progress '
               'notification.', required=False)
    )
    def testProgress(self, params):
        test = params.get('test', 'success')
        duration = int(params.get('duration', 10))
        resourceId = params.get('resourceId', None)
        resourceName = params.get('resourceName', None)
        startTime = time.time()
        with ProgressContext(True, user=self.getCurrentUser(),
                             title='Progress Test', message='Progress Message',
                             total=duration, resource={'_id': resourceId},
                             resourceName=resourceName) as ctx:
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
        folder = Folder().load(params['folderId'], force=True)

        upload = Upload().createUpload(
            user=self.getCurrentUser(), name=name, parentType='folder',
            parent=folder, size=os.path.getsize(path))

        with open(path, 'rb') as fd:
            file = Upload().handleChunk(upload, fd)

        return file

    @access.public
    @describeRoute(None)
    def registerAccessFlags(self, params):
        """
        Helper that can be used to register access flags in the system. This is
        used to test the access flags UI since the core does not expose any flags.
        """
        flags = self.getBodyJson()
        for key, info in six.viewitems(flags):
            registerAccessFlag(key, info['name'], info['description'], info['admin'])


class WebClientTestCase(base.TestCase):
    def setUp(self):
        self.specFile = os.environ['SPEC_FILE']
        self.assetstoreType = os.environ['ASSETSTORE_TYPE']
        self.webSecurity = os.environ.get('WEB_SECURITY', 'true')
        if self.webSecurity != 'false':
            self.webSecurity = 'true'
        base.TestCase.setUp(self, self.assetstoreType)
        # One of the web client tests uses this db, so make sure it is cleared
        # ahead of time.  This still allows tests to be run in parallel, since
        # nothing should be stored in this db
        base.dropGridFSDatabase('girder_webclient_gridfs')

        testServer.root.api.v1.webclienttest = WebClientTestEndpoints()

        if 'SETUP_MODULES' in os.environ:
            import imp
            for i, script in enumerate(os.environ['SETUP_MODULES'].split(':')):
                imp.load_source('girder.web_test_setup%d' % i, script)

    def testWebClientSpec(self):
        baseUrl = '/static/built/testEnv.html'
        if os.environ.get('BASEURL', ''):
            baseUrl = os.environ['BASEURL']

        cmd = (
            'npx', 'phantomjs',
            '--web-security=%s' % self.webSecurity,
            os.path.join(ROOT_DIR, 'clients', 'web', 'test', 'specRunner.js'),
            'http://localhost:%s%s' % (os.environ['GIRDER_PORT'], baseUrl),
            self.specFile,
            os.environ.get('JASMINE_TIMEOUT', ''),
            # Disambiguate repeat tests run on the same spec file, by adding any non-default
            # assetstore types to the test output files
            self.assetstoreType if self.assetstoreType != 'filesystem' else ''
        )

        # phantomjs occasionally fails to load javascript files.  This appears
        # to be a known issue: https://github.com/ariya/phantomjs/issues/10652.
        # Retry several times if it looks like this has occurred.
        retry_count = os.environ.get('PHANTOMJS_RETRY', 3)
        for _ in range(int(retry_count)):
            retry = False
            task = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=ROOT_DIR)
            jasmineFinished = False
            for line in iter(task.stdout.readline, b''):
                if isinstance(line, six.binary_type):
                    line = line.decode('utf8')
                if ('PHANTOM_TIMEOUT' in line or 'error loading source script' in line):
                    task.kill()
                    retry = True
                elif '__FETCHEMAIL__' in line:
                    base.mockSmtp.waitForMail()
                    msg = base.mockSmtp.getMail(parse=True)
                    open('phantom_temp_%s.tmp' % os.environ['GIRDER_PORT'],
                         'wb').write(msg.get_payload(decode=True))
                    continue  # we don't want to print this
                if 'Testing Finished' in line:
                    jasmineFinished = True
                try:
                    sys.stdout.write(line)
                except UnicodeEncodeError:
                    sys.stdout.write(repr(line))
                sys.stdout.flush()
            returncode = task.wait()
            if not retry and jasmineFinished:
                break
            sys.stderr.write('Retrying test\n')
            # If we are retrying, we need to reset the whole test, as the
            # databases and other resources are in an unknown state
            self.tearDown()
            self.setUp()

        self.assertEqual(returncode, 0)
