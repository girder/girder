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
import logging
import os
import shutil
import signal
import six
import sys
import unittest
import uuid

from six import BytesIO
from six.moves import urllib
from girder.utility import model_importer
from girder.utility.server import setup as setupServer
from girder.constants import AccessType, ROOT_DIR, SettingKey
from girder.models import getDbConnection
from . import mock_smtp
from . import mock_s3
from . import mongo_replicaset

local = cherrypy.lib.httputil.Host('127.0.0.1', 30000)
remote = cherrypy.lib.httputil.Host('127.0.0.1', 30001)
mockSmtp = mock_smtp.MockSmtpReceiver()
mockS3Server = None
enabledPlugins = []


def startServer(mock=True, mockS3=False):
    """
    Test cases that communicate with the server should call this
    function in their setUpModule() function.
    """
    server = setupServer(test=True, plugins=enabledPlugins)

    if mock:
        cherrypy.server.unsubscribe()

    cherrypy.engine.start()

    # Make server quiet (won't announce start/stop or requests)
    cherrypy.config.update({'environment': 'embedded'})

    # Log all requests if we asked to do so
    if 'cherrypy' in os.environ.get('EXTRADEBUG', '').split():
        cherrypy.config.update({'log.screen': True})
        logHandler = logging.StreamHandler(sys.stdout)
        logHandler.setLevel(logging.DEBUG)
        cherrypy.log.error_log.addHandler(logHandler)

    mockSmtp.start()
    if mockS3:
        global mockS3Server
        mockS3Server = mock_s3.startMockS3Server()

    return server


def stopServer():
    """
    Test cases that communicate with the server should call this
    function in their tearDownModule() function.
    """
    cherrypy.engine.exit()
    mockSmtp.stop()


def dropTestDatabase(dropModels=True):
    """
    Call this to clear all contents from the test database. Also forces models
    to reload.
    """
    db_connection = getDbConnection()

    dbName = cherrypy.config['database']['uri'].split('/')[-1]

    if 'girder_test_' not in dbName:
        raise Exception('Expected a testing database name, but got %s' % dbName)
    db_connection.drop_database(dbName)

    if dropModels:
        model_importer.reinitializeAll()


def dropGridFSDatabase(dbName):
    """
    Clear all contents from a gridFS database used as an assetstore.
    :param dbName: the name of the database to drop.
    """
    db_connection = getDbConnection()
    db_connection.drop_database(dbName)


def dropFsAssetstore(path):
    """
    Delete all of the files in a filesystem assetstore.  This unlinks the path,
    which is potentially dangerous.
    :param path: the path to remove.
    """
    if os.path.isdir(path):
        shutil.rmtree(path)


class TestCase(unittest.TestCase, model_importer.ModelImporter):
    """
    Test case base class for the application. Adds helpful utilities for
    database and HTTP communication.
    """
    def setUp(self, assetstoreType=None, dropModels=True):
        """
        We want to start with a clean database each time, so we drop the test
        database before each test. We then add an assetstore so the file model
        can be used without 500 errors.
        :param assetstoreType: if 'gridfs' or 's3', use that assetstore.  For
                               any other value, use a filesystem assetstore.
        """
        self.assetstoreType = assetstoreType
        dropTestDatabase(dropModels=dropModels)
        assetstoreName = os.environ.get('GIRDER_TEST_ASSETSTORE', 'test')
        assetstorePath = os.path.join(
            ROOT_DIR, 'tests', 'assetstore', assetstoreName)
        if assetstoreType == 'gridfs':
            # Name this as '_auto' to prevent conflict with assetstores created
            # within test methods
            gridfsDbName = 'girder_test_%s_assetstore_auto' % assetstoreName
            dropGridFSDatabase(gridfsDbName)
            self.assetstore = self.model('assetstore'). \
                createGridFsAssetstore(name='Test', db=gridfsDbName)
        elif assetstoreType == 'gridfsrs':
            gridfsDbName = 'girder_test_%s_rs_assetstore_auto' % assetstoreName
            mongo_replicaset.startMongoReplicaSet()
            self.assetstore = self.model('assetstore'). \
                createGridFsAssetstore(
                name='Test', db=gridfsDbName,
                mongohost='mongodb://127.0.0.1:27070,127.0.0.1:27071,'
                '127.0.0.1:27072', replicaset='replicaset')
        elif assetstoreType == 's3':
            self.assetstore = self.model('assetstore'). \
                createS3Assetstore(name='Test', bucket='bucketname',
                                   accessKeyId='test', secret='test',
                                   service=mockS3Server.service)
        else:
            dropFsAssetstore(assetstorePath)
            self.assetstore = self.model('assetstore'). \
                createFilesystemAssetstore(name='Test', root=assetstorePath)

        addr = ':'.join(map(str, mockSmtp.address))
        self.model('setting').set(SettingKey.SMTP_HOST, addr)
        self.model('setting').set(SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE, 0)
        self.model('setting').set(SettingKey.PLUGINS_ENABLED, enabledPlugins)

    def tearDown(self):
        """
        Stop any services that we started just for this test.
        """
        # If "self.setUp" is overridden, "self.assetstoreType" may not be set
        if getattr(self, 'assetstoreType', None) == 'gridfsrs':
            mongo_replicaset.stopMongoReplicaSet()

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

        if not response.output_status.startswith(code.encode()):
            msg = 'Response status was %s, not %s.' % (response.output_status,
                                                       code)

            if hasattr(response, 'json'):
                msg += ' Response body was:\n%s' % json.dumps(
                    response.json, sort_keys=True, indent=4,
                    separators=(',', ': '))

            self.fail(msg)

    def assertHasKeys(self, obj, keys):
        """
        Assert that the given object has the given list of keys.

        :param obj: The dictionary object.
        :param keys: The keys it must contain.
        :type keys: list or tuple
        """
        for k in keys:
            self.assertTrue(k in obj, 'Object does not contain key "%s"' % k)

    def assertRedirect(self, resp, url=None):
        """
        Assert that we were given an HTTP redirect response, and optionally
        assert that you were redirected to a specific URL.

        :param resp: The response object.
        :param url: If you know the URL you expect to be redirected to, you
            should pass it here.
        :type url: str
        """
        self.assertStatus(resp, 303)
        self.assertTrue('Location' in resp.headers)

        if url:
            self.assertEqual(url, resp.headers['Location'])

    def assertNotHasKeys(self, obj, keys):
        """
        Assert that the given object does not have any of the given list of
        keys.

        :param obj: The dictionary object.
        :param keys: The keys it must not contain.
        :type keys: list or tuple
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

    def getSseMessages(self, resp):
        messages = self.getBody(resp).strip().split('\n\n')
        if not messages or messages == ['']:
            return ()
        return [json.loads(m.replace('data: ', '')) for m in messages]

    def uploadFile(self, name, contents, user, parent, parentType='folder',
                   mimeType=None):
        """
        Upload a file. This is meant for small testing files, not very large
        files that should be sent in multiple chunks.

        :param name: The name of the file.
        :type name: str
        :param contents: The file contents
        :type contents: str
        :param user: The user performing the upload.
        :type user: dict
        :param parent: The parent document.
        :type parent: dict
        :param parentType: The type of the parent ("folder" or "item")
        :type parentType: str
        :param mimeType: Explicit MIME type to set on the file.
        :type mimeType: str
        :returns: The file that was created.
        :rtype: dict
        """
        mimeType = mimeType or 'application/octet-stream'
        resp = self.request(
            path='/file', method='POST', user=user, params={
                'parentType': parentType,
                'parentId': str(parent['_id']),
                'name': name,
                'size': len(contents),
                'mimeType': mimeType
            })
        self.assertStatusOk(resp)

        fields = [('offset', 0), ('uploadId', resp.json['_id'])]
        files = [('chunk', name, contents)]
        resp = self.multipartRequest(
            path='/file/chunk', user=user, fields=fields, files=files)
        self.assertStatusOk(resp)

        file = resp.json
        self.assertHasKeys(file, ['itemId'])
        self.assertEqual(file['name'], name)
        self.assertEqual(file['size'], len(contents))
        self.assertEqual(file['mimeType'], mimeType)

        return self.model('file').load(file['_id'], force=True)

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

    def _genToken(self, user):
        """
        Helper method for creating an authentication token for the user.
        """
        token = self.model('token').createToken(user)
        return str(token['_id'])

    def _buildHeaders(self, headers, cookie, user, token, basicAuth,
                      authHeader):
        if cookie is not None:
            headers.append(('Cookie', cookie))

        if user is not None:
            headers.append(('Girder-Token', self._genToken(user)))
        elif token is not None:
            if isinstance(token, dict):
                headers.append(('Girder-Token', token['_id']))
            else:
                headers.append(('Girder-Token', token))

        if basicAuth is not None:
            auth = base64.b64encode(basicAuth.encode('utf8'))
            headers.append((authHeader, 'Basic %s' % auth.decode()))

    def request(self, path='/', method='GET', params=None, user=None,
                prefix='/api/v1', isJson=True, basicAuth=None, body=None,
                type=None, exception=False, cookie=None, token=None,
                additionalHeaders=None, useHttps=False,
                authHeader='Girder-Authorization'):
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
        :param token: If you want to use an existing token to login, pass
            the token ID.
        :type token: str
        :param additionalHeaders: A list of headers to add to the
                                  request.  Each item is a tuple of the form
                                  (header-name, header-value).
        :param useHttps: If True, pretend to use HTTPS.
        :param authHeader: The HTTP request header to use for authentication.
        :type authHeader: str
        :returns: The cherrypy response object from the request.
        """
        if not params:
            params = {}

        headers = [('Host', '127.0.0.1'), ('Accept', 'application/json')]
        qs = fd = None

        if additionalHeaders:
            headers.extend(additionalHeaders)
        if method in ['POST', 'PUT', 'PATCH'] or body:
            if isinstance(body, six.string_types):
                body = body.encode('utf8')
            qs = urllib.parse.urlencode(params).encode('utf8')
            if type is None:
                headers.append(('Content-Type',
                                'application/x-www-form-urlencoded'))
            else:
                headers.append(('Content-Type', type))
                qs = body
            headers.append(('Content-Length', '%d' % len(qs)))
            fd = BytesIO(qs)
            qs = None
        elif params:
            qs = urllib.parse.urlencode(params)

        app = cherrypy.tree.apps['']
        request, response = app.get_serving(
            local, remote, 'http' if not useHttps else 'https', 'HTTP/1.1')
        request.show_tracebacks = True

        self._buildHeaders(headers, cookie, user, token, basicAuth, authHeader)

        # Python2 will not match Unicode URLs
        url = str(prefix + path)
        try:
            response = request.run(method, url, qs, 'HTTP/1.1', headers, fd)
        finally:
            if fd:
                fd.close()

        if isJson:
            body = self.getBody(response)
            try:
                response.json = json.loads(body)
            except Exception:
                print(body)
                raise AssertionError('Did not receive JSON response')

        if not exception and response.output_status.startswith(b'500'):
            raise AssertionError("Internal server error: %s" %
                                 self.getBody(response))

        return response

    def getBody(self, response, text=True):
        """
        Returns the response body as a text type or binary string.

        :param response: The response object from the server.
        :param text: If true, treat the data as a text string, otherwise, treat
                     as binary.
        """
        data = '' if text else b''

        for chunk in response.body:
            if text and isinstance(chunk, six.binary_type):
                chunk = chunk.decode('utf8')
            elif not text and not isinstance(chunk, six.binary_type):
                chunk = chunk.encode('utf8')
            data += chunk

        return data

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
            headers.append(('Girder-Token', self._genToken(user)))

        fd = io.BytesIO(body)
        # Python2 will not match Unicode URLs
        url = str(prefix + path)
        try:
            response = request.run(method, url, None, 'HTTP/1.1', headers, fd)
        finally:
            fd.close()

        if isJson:
            body = self.getBody(response)
            try:
                response.json = json.loads(body)
            except Exception:
                print(body)
                raise AssertionError('Did not receive JSON response')

        if response.output_status.startswith(b'500'):
            raise AssertionError("Internal server error: %s" %
                                 self.getBody(response))

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
            'multipart/form-data; boundary=%s' % self.boundary

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
            yield encoder('--%s\r\n' % self.boundary)
            yield encoder(self.u('Content-Disposition: form-data; '
                                 'name="%s"\r\n') % key)
            yield encoder('\r\n')
            if isinstance(value, int) or isinstance(value, float):
                value = str(value)
            yield encoder(self.u(value))
            yield encoder('\r\n')
        for (key, filename, content) in files:
            key = self.u(key)
            filename = self.u(filename)
            yield encoder('--%s\r\n' % self.boundary)
            yield encoder(self.u('Content-Disposition: form-data; name="%s";'
                          ' filename="%s"\r\n' % (key, filename)))
            yield encoder('Content-Type: application/octet-stream\r\n')
            yield encoder('\r\n')

            yield (content, len(content))
            yield encoder('\r\n')
        yield encoder('--%s--\r\n' % self.boundary)

    def encode(self, fields, files):
        body = io.BytesIO()
        size = 0
        for chunk, chunkLen in self.iter(fields, files):
            if not isinstance(chunk, six.binary_type):
                chunk = chunk.encode('utf8')
            body.write(chunk)
            size += chunkLen
        return self.contentType, body.getvalue(), size


def _sigintHandler(*args):
    print('Received SIGINT, shutting down mock SMTP server...')
    mockSmtp.stop()
    sys.exit(1)


signal.signal(signal.SIGINT, _sigintHandler)
