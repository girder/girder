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

from .. import base

from girder.api import access, describe, docs
from girder.api.rest import Resource

OrderedRoutes = [
    ('GET', (), ''),
    ('GET', (':id',), '/{id}'),
    ('UNKNOWN', (':id',), '/{id}'),
    ('GET', (':id', 'action'), '/{id}/action'),
    ('GET', ('action',), '/action'),
    ('PUT', ('action',), '/action'),
    ('POST', ('action',), '/action'),
    ('PATCH', ('action',), '/action'),
    ('DELETE', ('action',), '/action'),
    ('NEWMETHOD', ('action',), '/action'),
    ('UNKNOWN', ('action',), '/action'),
    ('GET', ('action', ':id'), '/action/{id}'),
    ('GET', ('noaction',), '/noaction')
    ]


class DummyResource(Resource):
    def __init__(self):
        super(DummyResource, self).__init__()
        self.resourceName = 'foo'
        for method, pathElements, testPath in OrderedRoutes:
            self.route(method, pathElements, self.handler)

    @access.public
    @describe.describeRoute(
        describe.Description('Does nothing')
    )
    def handler(self, **kwargs):
        return kwargs


testModel = {
    'id': 'Body',
    'require': 'bob',
    'properties': {
        'bob': {
            'type': 'array',
            'items': {
                'type': 'integer'
            }
        }
    }
}
docs.addModel('Body', testModel, resources='model')

globalModel = {
    'id': 'Global',
    'properties': {}
}
docs.addModel('Global', globalModel)


class ModelResource(Resource):
    def __init__(self):
        super(ModelResource, self).__init__()
        self.resourceName = 'model'
        self.route('POST', (), self.hasModel)

    @access.public
    @describe.describeRoute(
        describe.Description('What a model')
        .param('body', 'Where its at!', dataType='Body', required=True,
               paramType='body')
    )
    def hasModel(self, params):
        pass


def setUpModule():
    server = base.startServer()
    server.root.api.v1.accesstest = DummyResource()
    server.root.api.v1.modeltest = ModelResource()


def tearDownModule():
    base.stopServer()


class ApiDescribeTestCase(base.TestCase):
    """
    Makes sure our swagger auto API docs are working.
    """

    def testInvalidResource(self):
        methods = ['DELETE', 'GET', 'PATCH', 'POST', 'PUT']

        for m in methods:
            resp = self.request(path='/not_valid', method=m, isJson=False)
            self.assertStatus(resp, 404)

        methods.remove('GET')
        for m in methods:
            resp = self.request(path='', method=m, isJson=False)
            self.assertStatus(resp, 405)

    def testApiDescribe(self):
        # Get coverage for serving the static swagger page
        resp = self.request(path='', method='GET', isJson=False)
        self.assertStatusOk(resp)

        # Test top level describe endpoint
        resp = self.request(path='/describe', method='GET')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['swaggerVersion'], describe.SWAGGER_VERSION)
        self.assertEqual(resp.json['apiVersion'], describe.API_VERSION)
        self.assertTrue({'path': '/group'} in resp.json['apis'])

        # Request a specific resource's description, sanity check
        resp = self.request(path='/describe/user', method='GET')
        self.assertStatusOk(resp)
        for routeDoc in resp.json['apis']:
            self.assertHasKeys(('path', 'operations'), routeDoc)
            self.assertTrue(len(routeDoc['operations']) > 0)

        # Request an unknown resource's description to get an error
        resp = self.request(path='/describe/unknown', method='GET')
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Invalid resource: unknown')

    def testRouteOrder(self):
        # Check that the resources and operations are listed in the order we
        # expect
        resp = self.request(path='/describe/foo', method='GET')
        self.assertStatusOk(resp)
        listedRoutes = [(method['httpMethod'], route['path'])
                        for route in resp.json['apis']
                        for method in route['operations']]
        expectedRoutes = [(method, '/foo'+testPath)
                          for method, pathElements, testPath in OrderedRoutes]
        self.assertEqual(listedRoutes, expectedRoutes)

    def testAddModel(self):
        resp = self.request(path='/describe/model')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['models'], {
            'Body': testModel,
            'Global': globalModel
        })

        resp = self.request(path='/describe/folder')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['models'],
                         dict(Global=globalModel, **docs.models['folder']))
