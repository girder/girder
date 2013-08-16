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

import cherrypy
import json
import unittest
import urllib

from StringIO import StringIO
from girder.utility.model_importer import ModelImporter
from girder.utility.server import setup as setupServer
from girder.constants import AccessType

local = cherrypy.lib.httputil.Host('127.0.0.1', 50000, '')
remote = cherrypy.lib.httputil.Host('127.0.0.1', 50001, '')


def startServer():
    """
    Test cases that communicate with the server should call this
    function in their setUpModule() function.
    """
    setupServer(test=True)

    # Make server quiet (won't announce start/stop or requests)
    cherrypy.config.update({'environment': 'embedded'})

    cherrypy.server.unsubscribe()
    cherrypy.engine.start()


def stopServer():
    """
    Test cases that communicate with the server should call this
    function in their tearDownModule() function.
    """
    cherrypy.engine.exit()


def dropTestDatabase():
    """
    Call this to clear all contents from the test database.
    """
    from girder.models import db_connection
    db_connection.drop_database('%s_test' %
                                cherrypy.config['database']['database'])


class TestCase(unittest.TestCase, ModelImporter):
    """
    Test case base class for the application. Adds helpful utilities for
    database and HTTP communication.
    """
    def setUp(self):
        """
        We want to start with a clean database each time, so we drop the test
        database before each test.
        """
        dropTestDatabase()

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
        msg = 'Response status was not %s' % code
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

    def assertAccessDenied(self, response, level, modelName):
        if level == AccessType.READ:
            ls = 'Read'
        elif level == AccessType.WRITE:
            ls = 'Write'
        else:
            ls = 'Admin'
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

    def ensureRequiredParams(self, path='/', method='GET', required=()):
        """
        Ensure that a set of parameters is required by the endpoint.

        :param path: The endpoint path to test.
        :param method: The HTTP method of the endpoint.
        :param required: The required parameter set.
        :type required: sequence of str
        """
        for exclude in required:
            params = dict.fromkeys([p for p in required if p != exclude], '')
            resp = self.request(path=path, method=method, params=params)
            self.assertMissingParameter(resp, exclude)

    def request(self, path='/', method='GET', params={}, user=None,
                prefix='/api/v1', isJson=True):
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
        :returns: The cherrypy response object from the request.
        """
        headers = [('Host', '127.0.0.1'), ('Accept', 'application/json')]
        qs = fd = None

        if method in ['POST', 'PUT']:
            qs = urllib.urlencode(params)
            headers.append(('Content-Type',
                            'application/x-www-form-urlencoded'))
            headers.append(('Content-Length', '%d' % len(qs)))
            fd = StringIO(qs)
            qs = None
        elif params:
            qs = urllib.urlencode(params)

        app = cherrypy.tree.apps['']
        request, response = app.get_serving(local, remote, 'http', 'HTTP/1.1')

        if user is not None:
            token = self.model('token').createToken(user)
            cookie = json.dumps({
                'userId': str(user['_id']),
                'token': str(token['_id'])
                }).replace('"', "\\\"")
            headers.append(('Cookie', 'authToken="%s"' % cookie))
        try:
            response = request.run(method, prefix + path, qs, 'HTTP/1.1',
                                   headers, fd)
        finally:
            if fd:
                fd.close()
                fd = None

        if isJson:
            response.json = json.loads(response.collapse_body())

        if response.output_status.startswith('500'):
            raise AssertionError("Internal server error: %s" % response.body)

        return response
