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

import datetime
import json
from .. import base

from girder.api import access, describe, docs
from girder.api.rest import Resource

server = None
Routes = [
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
        for method, pathElements, testPath in Routes:
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
    global server
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
        self.assertHasKeys(resp.json, ('basePath', 'host', 'definitions',
                                       'info', 'paths', 'swagger', 'tags'))
        self.assertHasKeys(resp.json['info'], ('title', 'version'))
        self.assertEqual(resp.json['swagger'], describe.SWAGGER_VERSION)
        self.assertEqual(resp.json['info']['version'], describe.API_VERSION)
        self.assertIn('/group', resp.json['paths'])
        self.assertIn({'name': 'group'}, resp.json['tags'])
        self.assertHasKeys(
            resp.json['paths']['/group'], ('get', 'post'))
        self.assertHasKeys(
            resp.json['paths']['/group']['get'],
            ('operationId', 'parameters', 'responses'))
        self.assertHasKeys(
            resp.json['paths']['/group']['post'],
            ('operationId', 'parameters', 'responses'))
        self.assertGreater(len(
            resp.json['paths']['/group']['get']['operationId']), 0)
        self.assertGreater(len(
            resp.json['paths']['/group']['get']['parameters']), 0)
        self.assertGreater(len(
            resp.json['paths']['/group']['get']['responses']), 0)
        param = resp.json['paths']['/group']['get']['parameters'][0]
        self.assertHasKeys(
            param,
            ('description', 'in', 'name', 'required', 'type'))
        self.assertGreater(len(param['description']), 0)
        self.assertGreater(len(param['in']), 0)
        self.assertGreater(len(param['name']), 0)
        self.assertGreater(len(param['type']), 0)
        self.assertTrue(isinstance(param['required'], bool))
        self.assertIn(
            '200',
            resp.json['paths']['/group']['get']['responses'])
        self.assertIn(
            'description',
            resp.json['paths']['/group']['get']['responses']['200'])

    def testRoutesExist(self):
        # Check that the resources and operations exist
        resp = self.request(path='/describe', method='GET')
        self.assertStatusOk(resp)
        self.assertHasKeys(
            resp.json['paths'],
            ('/foo', '/foo/{id}', '/foo/{id}/action', '/foo/action',
             '/foo/action/{id}', '/foo/noaction'))
        self.assertHasKeys(
            resp.json['paths']['/foo'],
            ('get',))
        self.assertEqual(len(resp.json['paths']['/foo']), 1)
        self.assertHasKeys(
            resp.json['paths']['/foo/{id}'],
            ('get', 'unknown'))
        self.assertEqual(len(resp.json['paths']['/foo/{id}']), 2)
        self.assertHasKeys(
            resp.json['paths']['/foo/{id}/action'],
            ('get',))
        self.assertEqual(len(resp.json['paths']['/foo/{id}/action']), 1)
        self.assertHasKeys(
            resp.json['paths']['/foo/action'],
            ('get', 'put', 'post', 'patch', 'delete', 'newmethod', 'unknown'))
        self.assertEqual(len(resp.json['paths']['/foo/action']), 7)
        self.assertHasKeys(
            resp.json['paths']['/foo/action/{id}'],
            ('get',))
        self.assertEqual(len(resp.json['paths']['/foo/action/{id}']), 1)
        self.assertHasKeys(
            resp.json['paths']['/foo/noaction'],
            ('get',))
        self.assertEqual(len(resp.json['paths']['/foo/noaction']), 1)

    def testAddModel(self):
        resp = self.request(path='/describe')
        self.assertStatusOk(resp)
        self.assertTrue('definitions' in resp.json)
        self.assertHasKeys(('Body', 'Global'), resp.json['definitions'])
        self.assertEqual(resp.json['definitions']['Body'], testModel)
        self.assertEqual(resp.json['definitions']['Global'], globalModel)

    def testAutoDescribeRoute(self):
        testRuns = []

        class AutoDescribe(Resource):
            def __init__(self):
                super(AutoDescribe, self).__init__()
                self.resourceName = 'auto_describe'
                self.route('GET', ('test',), self.test)

            @access.public
            @describe.autoDescribeRoute(
                describe.Description('test')
                .param('b1', '', dataType='boolean', required=False, default=True)
                .param('b2', '', dataType='boolean', required=False)
                .param('float', '', dataType='number', required=False, default=1.0)
                .param('integer', '', dataType='integer', required=False)
                .param('timestamp', '', dataType='dateTime', required=False)
                .param('datestamp', '', dataType='date', required=False)
                .param('string', '', enum=['hello', 'world'], strip=True, lower=True)
                .jsonParam('json1', '', required=False, requireArray=True)
                .jsonParam('json2', '', required=False, requireObject=True, default={})
            )
            def test(self, b1, b2, string, integer, float, timestamp, datestamp, json1, json2,
                     params):
                testRuns.append({
                    'b1': b1,
                    'b2': b2,
                    'string': string,
                    'integer': integer,
                    'float': float,
                    'timestamp': timestamp,
                    'datestamp': datestamp,
                    'json1': json1,
                    'json2': json2
                })

        server.root.api.v1.auto_describe = AutoDescribe()

        def testBad(inputs, expected):
            resp = self.request('/auto_describe/test', params=inputs)
            self.assertStatus(resp, 400)
            self.assertEqual(testRuns, [])
            self.assertEqual(resp.json['message'], expected)

        def testOk(inputs, expected):
            resp = self.request('/auto_describe/test', params=inputs)
            self.assertStatusOk(resp)
            self.assertEqual(len(testRuns), 1)
            self.assertEqual(testRuns[0], expected)
            del testRuns[-1]

        testBad({}, 'Parameter "string" is required.')
        testBad({
            'string': 'invalid value'
        }, 'Invalid value for string: "invalid value". Allowed values: hello, world.')
        testBad({
            'string': 'hello',
            'float': 'not a float'
        }, 'Invalid value for numeric parameter float: not a float.')

        testBad({
            'string': 'hello',
            'integer': '7.5'
        }, 'Invalid value for integer parameter integer: 7.5.')

        testBad({
            'string': 'hello',
            'timestamp': 'hello world'
        }, 'Invalid date format for parameter timestamp: hello world.')

        testBad({
            'string': 'hello',
            'datestamp': 'not a date'
        }, 'Invalid date format for parameter datestamp: not a date.')

        testBad({
            'string': 'hello',
            'json1': json.dumps({'hello': 'world'})
        }, 'Parameter json1 must be a JSON array.')

        testBad({
            'string': 'hello',
            'json2': json.dumps(['hello', 'world'])
        }, 'Parameter json2 must be a JSON object.')

        testOk({
            'string': '  WoRlD '
        }, {
            'string': 'world',
            'b1': True,
            'b2': None,
            'integer': None,
            'float': 1.,
            'json1': None,
            'json2': {},
            'timestamp': None,
            'datestamp': None
        })

        testOk({
            'string': ' hello',
            'b1': 'false',
            'b2': 'true',
            'integer': '3',
            'float': '0.25',
            'json1': json.dumps([1, 2, 'abc']),
            'json2': json.dumps({'hello': 'world'}),
            'timestamp': '2017-01-01T11:35:22',
            'datestamp': '2017-02-02T11:33:22'
        }, {
            'string': 'hello',
            'b1': False,
            'b2': True,
            'integer': 3,
            'float': 0.25,
            'json1': [1, 2, 'abc'],
            'json2': {'hello': 'world'},
            'timestamp': datetime.datetime(2017, 1, 1, 11, 35, 22),
            'datestamp': datetime.date(2017, 2, 2)
        })
