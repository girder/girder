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

import base64
import codecs
import cherrypy
import io
import json
import os
import signal
import sys
import unittest
import urllib
import uuid

from StringIO import StringIO
from girder.utility import model_importer
from girder.utility.server import setup as setupServer
from girder.constants import AccessType, ROOT_DIR, SettingKey
from . import mock_smtp

local = cherrypy.lib.httputil.Host('127.0.0.1', 50000, '')
remote = cherrypy.lib.httputil.Host('127.0.0.1', 50001, '')
mockSmtp = mock_smtp.MockSmtpReceiver()
enabledPlugins = []


def startServer(mock=True):
    """
    Test cases that communicate with the server should call this
    function in their setUpModule() function.
    """
    setupServer(test=True, plugins=enabledPlugins)

    # Make server quiet (won't announce start/stop or requests)
    cherrypy.config.update({'environment': 'embedded'})

    if mock:
        cherrypy.server.unsubscribe()

    cherrypy.engine.start()

    mockSmtp.start()


def stopServer():
    """
    Test cases that communicate with the server should call this
    function in their tearDownModule() function.
    """
    cherrypy.engine.exit()
    mockSmtp.stop()


def dropTestDatabase():
    """
    Call this to clear all contents from the test database. Also forces models
    to reload.
    """
    from girder.models import getDbConnection
    db_connection = getDbConnection()
    model_importer.clearModels()  # Must clear the models so indices are rebuilt
    dbName = cherrypy.config['database']['database']

    if 'girder_test_' not in dbName:
        raise Exception('Expected a testing database name, but got {}'
                        .format(dbName))
    db_connection.drop_database(dbName)


class TestCase(unittest.TestCase, model_importer.ModelImporter):
    """
    Test case base class for the application. Adds helpful utilities for
    database and HTTP communication.
    """
    def setUp(self):
        """
        We want to start with a clean database each time, so we drop the test
        database before each test. We then add an assetstore so the file model
        can be used without 500 errors.
        """
        dropTestDatabase()
        assetstorePath = os.path.join(
            ROOT_DIR, 'tests', 'assetstore',
            os.environ.get('GIRDER_TEST_ASSETSTORE', 'test'))
        self.assetstore = self.model('assetstore').createFilesystemAssetstore(
            name='Test', root=assetstorePath)

        addr = ':'.join(map(str, mockSmtp.address))
        self.model('setting').set(SettingKey.SMTP_HOST, addr)

    def assertStatusOk(self, response):
        """
        Call this to assert that the response yielded a 200 OK output_status.

        :param response: The response object.
        """
        self.assertStatus(response, 200)

    def assertStatus(self, response, code):
        """
        Call this to assert that a given HTTP status code was returned.

        :param response: The response object.
        :param code: The status code.
        :type code: int or str
        """
        code = str(code)
        msg = 'Response status was %s, not %s.' % (response.output_status, code)
        self.assertTrue(response.output_status.startswith(code), msg)

    def assertHasKeys(self, obj, keys):
        """
        Assert that the given object has the given list of keys.

        :param obj: The dictionary object.
        :param keys: The keys it must contain.
        :type keys: list
        """
        for k in keys:
            self.assertTrue(k in obj, 'Object does not contain key "%s"' % k)

    def assertNotHasKeys(self, obj, keys):
        """
        Assert that the given object does not have any of the given list of
        keys.

        :param obj: The dictionary object.
        :param keys: The keys it must not contain.
        :type keys: list
        """
        for k in keys:
            self.assertFalse(k in obj, 'Object contains key "%s"' % k)

    def assertValidationError(self, response, field=None):
        """
        Assert that a ValidationException was thrown with the given field.

        :param response: The response object.
        :param field: The field that threw the validation exception.
        :type field: str
        """
        self.assertStatus(response, 400)
        self.assertEqual(response.json['type'], 'validation')
        self.assertEqual(response.json.get('field', None), field)

    def assertAccessDenied(self, response, level, modelName, user=None):
        if level == AccessType.READ:
            ls = 'Read'
        elif level == AccessType.WRITE:
            ls = 'Write'
        else:
            ls = 'Admin'

        if user is None:
            self.assertStatus(response, 401)
        else:
            self.assertStatus(response, 403)

        self.assertEqual('%s access denied for %s.' % (ls, modelName),
                         response.json['message'])

    def assertMissingParameter(self, response, param):
        """
        Assert that the response was a "parameter missing" error response.

        :param response: The response object.
        :param param: The name of the missing parameter.
        :type param: str
        """
        self.assertEqual("Parameter '%s' is required." % param,
                         response.json.get('message', ''))
        self.assertStatus(response, 400)

    def ensureRequiredParams(self, path='/', method='GET', required=(),
                             user=None):
        """
        Ensure that a set of parameters is required by the endpoint.

        :param path: The endpoint path to test.
        :param method: The HTTP method of the endpoint.
        :param required: The required parameter set.
        :type required: sequence of str
        """
        for exclude in required:
            params = dict.fromkeys([p for p in required if p != exclude], '')
            resp = self.request(path=path, method=method, params=params,
                                user=user)
            self.assertMissingParameter(resp, exclude)

    def _genCookie(self, user):
        """
        Helper method for creating an authentication cookie for the user.
        """
        token = self.model('token').createToken(user)
        cookie = json.dumps({
            'userId': str(user['_id']),
            'token': str(token['_id'])
        }).replace('"', "\\\"")
        return 'authToken="%s"' % cookie

    def request(self, path='/', method='GET', params={}, user=None,
                prefix='/api/v1', isJson=True, basicAuth=None, body=None,
                type=None, exception=False, cookie=None):
        """
        Make an HTTP request.

        :param path: The path part of the URI.
        :type path: str
        :param method: The HTTP method.
        :type method: str
        :param params: The HTTP parameters.
        :type params: dict
        :param prefix: The prefix to use before the path.
        :param isJson: Whether the response is a JSON object.
        :param basicAuth: A string to pass with the Authorization: Basic header
                          of the form 'login:password'
        :param exception: Set this to True if a 500 is expected from this call.
        :param cookie: A custom cookie value to set.
        :returns: The cherrypy response object from the request.
        """
        headers = [('Host', '127.0.0.1'), ('Accept', 'application/json')]
        qs = fd = None

        if method in ['POST', 'PUT']:
            qs = urllib.urlencode(params)
            if type is None:
                headers.append(('Content-Type',
                                'application/x-www-form-urlencoded'))
            else:
                headers.append(('Content-Type', type))
                qs = body
            headers.append(('Content-Length', '%d' % len(qs)))
            fd = StringIO(qs)
            qs = None
        elif params:
            qs = urllib.urlencode(params)

        app = cherrypy.tree.apps['']
        request, response = app.get_serving(local, remote, 'http', 'HTTP/1.1')
        request.show_tracebacks = True

        if cookie is not None:
            headers.append(('Cookie', cookie))
        elif user is not None:
            headers.append(('Cookie', self._genCookie(user)))

        if basicAuth is not None:
            authToken = base64.b64encode(basicAuth)
            headers.append(('Authorization', 'Basic {}'.format(authToken)))

        try:
            response = request.run(method, prefix + path, qs, 'HTTP/1.1',
                                   headers, fd)
        finally:
            if fd:
                fd.close()

        if isJson:
            try:
                response.json = json.loads(response.collapse_body())
            except:
                print response.collapse_body()
                raise AssertionError('Did not receive JSON response')

        if not exception and response.output_status.startswith('500'):
            raise AssertionError("Internal server error: %s" % response.body)

        return response

    def multipartRequest(self, fields, files, path, method='POST', user=None,
                         prefix='/api/v1', isJson=True):
        """
        Make an HTTP request with multipart/form-data encoding. This can be
        used to send files with the request.

        :param fields: List of (name, value) tuples.
        :param files: List of (name, filename, content) tuples.
        :param path: The path part of the URI.
        :type path: str
        :param method: The HTTP method.
        :type method: str
        :param prefix: The prefix to use before the path.
        :param isJson: Whether the response is a JSON object.
        :returns: The cherrypy response object from the request.
        """
        contentType, body, size = MultipartFormdataEncoder().encode(
            fields, files)

        headers = [('Host', '127.0.0.1'),
                   ('Accept', 'application/json'),
                   ('Content-Type', contentType),
                   ('Content-Length', str(size))]

        app = cherrypy.tree.apps['']
        request, response = app.get_serving(local, remote, 'http', 'HTTP/1.1')
        request.show_tracebacks = True

        if user is not None:
            headers.append(('Cookie', self._genCookie(user)))

        fd = io.BytesIO(body)
        try:
            response = request.run(method, prefix + path, None, 'HTTP/1.1',
                                   headers, fd)
        finally:
            fd.close()

        if isJson:
            try:
                response.json = json.loads(response.collapse_body())
            except:
                print response.collapse_body()
                raise AssertionError('Did not receive JSON response')

        if response.output_status.startswith('500'):
            raise AssertionError("Internal server error: %s" % response.body)

        return response


class MultipartFormdataEncoder(object):
    """
    This class is adapted from http://stackoverflow.com/a/18888633/2550451

    It is used as a helper for creating multipart/form-data requests to
    simulate file uploads.
    """
    def __init__(self):
        self.boundary = uuid.uuid4().hex
        self.contentType = \
            'multipart/form-data; boundary={}'.format(self.boundary)

    @classmethod
    def u(cls, s):
        if sys.hexversion < 0x03000000 and isinstance(s, str):
            s = s.decode('utf-8')
        if sys.hexversion >= 0x03000000 and isinstance(s, bytes):
            s = s.decode('utf-8')
        return s

    def iter(self, fields, files):
        encoder = codecs.getencoder('utf-8')
        for (key, value) in fields:
            key = self.u(key)
            yield encoder('--{}\r\n'.format(self.boundary))
            yield encoder(self.u('Content-Disposition: form-data; '
                                 'name="{}"\r\n').format(key))
            yield encoder('\r\n')
            if isinstance(value, int) or isinstance(value, float):
                value = str(value)
            yield encoder(self.u(value))
            yield encoder('\r\n')
        for (key, filename, content) in files:
            key = self.u(key)
            filename = self.u(filename)
            yield encoder('--{}\r\n'.format(self.boundary))
            yield encoder(self.u('Content-Disposition: form-data; name="{}";'
                          ' filename="{}"\r\n').format(key, filename))
            yield encoder('Content-Type: application/octet-stream\r\n')
            yield encoder('\r\n')

            yield (content, len(content))
            yield encoder('\r\n')
        yield encoder('--{}--\r\n'.format(self.boundary))

    def encode(self, fields, files):
        body = io.BytesIO()
        size = 0
        for chunk, chunkLen in self.iter(fields, files):
            body.write(chunk)
            size += chunkLen
        return self.contentType, body.getvalue(), size


def _sigintHandler(*args):
    print 'Received SIGINT, shutting down mock SMTP server...'
    mockSmtp.stop()
    sys.exit(1)


signal.signal(signal.SIGINT, _sigintHandler)
