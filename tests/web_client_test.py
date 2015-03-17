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
import socket
import subprocess
import sys
import time

# Need to set the environment variable before importing girder
os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_PORT', '30001')  # noqa

from girder.api import access
from girder.api.describe import Description
from girder.api.rest import Resource, RestException
from girder.constants import ROOT_DIR
from girder.utility.progress import ProgressContext
from . import base

testServer = None


def setUpModule():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    girder_port = int(os.environ['GIRDER_PORT'])
    result = sock.connect_ex(('127.0.0.1', girder_port))
    if result == 0:
        sys.stderr.write('ERROR: Port %d already in use, perhaps a hung test?'
                         % (girder_port))

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
        self.route('GET', ('progress', ), self.testProgress)
        self.route('PUT', ('progress', 'stop'), self.testProgressStop)
        self.stop = False

    @access.token
    def testProgress(self, params):
        test = params.get('test', 'success')
        duration = int(params.get('duration', 10))
        startTime = time.time()
        with ProgressContext(True, user=self.getCurrentUser(),
                             title='Progress Test', message='Progress Message',
                             total=duration) as ctx:
            for current in xrange(duration):
                if self.stop:
                    break
                ctx.update(current=current)
                wait = startTime + current + 1 - time.time()
                if wait > 0:
                    time.sleep(wait)
            if test == 'error':
                raise RestException('Progress error test.')
    testProgress.description = (
        Description('Test progress contexts from the web')
        .param('test', 'Name of test to run.  These include "success" and '
               '"failure".', required=False)
        .param('duration', 'Duration of the test in seconds', required=False,
               dataType='int'))

    @access.token
    def testProgressStop(self, params):
        self.stop = True
    testProgressStop.description = (
        Description('Halt all progress tests'))


class WebClientTestCase(base.TestCase):
    def setUp(self):
        self.specFile = os.environ['SPEC_FILE']
        self.coverageFile = os.environ['COVERAGE_FILE']
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
        cmd = (
            os.path.join(
                ROOT_DIR, 'node_modules', 'phantomjs', 'bin', 'phantomjs'),
            '--web-security=%s' % self.webSecurity,
            os.path.join(ROOT_DIR, 'clients', 'web', 'test', 'specRunner.js'),
            'http://localhost:%s/static/built/testEnv.html' % os.environ[
                'GIRDER_PORT'],
            self.specFile,
            self.coverageFile,
            os.environ.get('JASMINE_TIMEOUT', '')
        )

        # phantomjs occasionally fails to load javascript files.  This appears
        # to be a known issue: https://github.com/ariya/phantomjs/issues/10652.
        # Retry several times if it looks like this has occurred.
        for tries in xrange(5):
            retry = False
            task = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            hasJasmine = False
            jasmineFinished = False
            for line in iter(task.stdout.readline, ''):
                if ('PHANTOM_TIMEOUT' in line or
                        'error loading source script' in line):
                    task.kill()
                    retry = True
                elif '__FETCHEMAIL__' in line:
                    base.mockSmtp.waitForMail()
                    msg = base.mockSmtp.getMail()
                    open('phantom_temp_%s.tmp' % os.environ['GIRDER_PORT'],
                         'wb').write(msg)
                    continue  # we don't want to print this
                if 'Jasmine' in line:
                    hasJasmine = True
                if 'Testing Finished' in line:
                    jasmineFinished = True
                sys.stdout.write(line)
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
