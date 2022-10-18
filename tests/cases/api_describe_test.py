# -*- coding: utf-8 -*-
import datetime
import json
from .. import base

from girder.api import access, describe, docs
from girder.api.rest import Resource, filtermodel
from girder.constants import AccessType, registerAccessFlag, VERSION
from girder.models.setting import Setting
from girder.models.user import User
from girder.settings import SettingKey

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
        super().__init__()
        self.resourceName = 'foo'
        for method, pathElements, _testPath in Routes:
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
        super().__init__()
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

    def testApiBrandName(self):
        resp = self.request(path='', method='GET', isJson=False)
        self.assertStatusOk(resp)
        body = self.getBody(resp)

        defaultBrandName = Setting().getDefault(SettingKey.BRAND_NAME)
        self.assertTrue(('<title>%s - REST API Documentation</title>' % defaultBrandName) in body)

        Setting().set(SettingKey.BRAND_NAME, 'FooBar')
        # An other request to check if the brand name is set
        resp = self.request(path='', method='GET', isJson=False)
        self.assertStatusOk(resp)
        body = self.getBody(resp)
        self.assertTrue(('<title>%s - REST API Documentation</title>' % 'FooBar') in body)

        Setting().unset(SettingKey.BRAND_NAME)
        resp = self.request(path='', method='GET', isJson=False)
        self.assertStatusOk(resp)
        body = self.getBody(resp)
        self.assertTrue(('<title>%s - REST API Documentation</title>' % defaultBrandName) in body)

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
        self.assertEqual(resp.json['info']['version'], VERSION['release'])
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

    def testApiDescribeReferred(self):
        resp = self.request(path='/describe', method='GET')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['basePath'], '/api/v1')
        self.assertEqual(resp.json['host'], '127.0.0.1')
        resp = self.request(
            path='/describe', method='GET',
            additionalHeaders=[('Referer', 'http://somewhere.com/alternate/api/v1')])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['basePath'], '/alternate/api/v1')
        self.assertEqual(resp.json['host'], 'somewhere.com')

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
        self.assertIn('Body', resp.json['definitions'])
        self.assertIn('Global', resp.json['definitions'])
        self.assertEqual(resp.json['definitions']['Body'], testModel)
        self.assertEqual(resp.json['definitions']['Global'], globalModel)

    def testAutoDescribeRoute(self):
        testRuns = []

        registerAccessFlag('my_flag', name='My flag')

        class AutoDescribe(Resource):
            def __init__(self):
                super().__init__()
                self.resourceName = 'auto_describe'
                self.route('GET', ('test',), self.test)
                self.route('POST', ('body',), self.body)
                self.route('POST', ('json_body',), self.jsonBody)
                self.route('POST', ('json_body_required',), self.jsonBodyRequired)
                self.route('GET', ('model_param_flags',), self.hasModelParamFlags)
                self.route('GET', ('model_param_query',), self.hasModelQueryParam)
                self.route('GET', ('json_schema',), self.hasJsonSchema)
                self.route('GET', ('missing_arg',), self.hasMissingArg)

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
                .param('upper', '', required=False, upper=True)
                .jsonParam('json1', '', required=False, requireArray=True)
                .jsonParam('json2', '', required=False, requireObject=True, default={})
            )
            def test(self, b1, b2, string, upper, integer, float, timestamp, datestamp, json1,
                     json2, params):
                testRuns.append({
                    'b1': b1,
                    'b2': b2,
                    'string': string,
                    'upper': upper,
                    'integer': integer,
                    'float': float,
                    'timestamp': timestamp,
                    'datestamp': datestamp,
                    'json1': json1,
                    'json2': json2
                })

            @access.public
            @describe.autoDescribeRoute(
                describe.Description('body')
                .param('body', '', required=False, paramType='body')
            )
            def body(self, body):
                testRuns.append({
                    'body': body
                })

            @access.public
            @describe.autoDescribeRoute(
                describe.Description('json_body')
                .jsonParam('json_body', '', required=False, paramType='body')
            )
            def jsonBody(self, json_body):
                testRuns.append({
                    'json_body': json_body
                })

            @access.public
            @describe.autoDescribeRoute(
                describe.Description('json_body_required')
                .jsonParam('json_body', '', required=True, requireObject=True, paramType='body')
            )
            def jsonBodyRequired(self, json_body):
                testRuns.append({
                    'json_body': json_body
                })

            @access.public
            @describe.autoDescribeRoute(
                describe.Description('has_model_param_query')
                .modelParam('userId', model='user', level=AccessType.READ, paramType='query')
            )
            @filtermodel(model='user')
            def hasModelQueryParam(self, user):
                return user

            @access.public
            @describe.autoDescribeRoute(
                describe.Description('has_model_param_flags')
                .modelParam('userId', model='user', level=AccessType.READ, paramType='query',
                            requiredFlags='my_flag')
            )
            def hasModelParamFlags(self, user):
                return user

            @access.public
            @describe.autoDescribeRoute(
                describe.Description('has_json_schema')
                .jsonParam('obj', '', schema={
                    'type': 'object',
                    'required': ['foo', 'bar']
                })
            )
            def hasJsonSchema(self, obj):
                return obj

            @access.public
            @describe.autoDescribeRoute(
                describe.Description('has_missing_arg')
                .param('foo', '')
            )
            def hasMissingArg(self, params):
                return params

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
            'upper': None,
            'b1': True,
            'b2': None,
            'integer': None,
            'float': 1.,
            'json1': None,
            'json2': '{}',
            'timestamp': None,
            'datestamp': None
        })

        testOk({
            'string': ' hello',
            'upper': ' hello',
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
            'upper': ' HELLO',
            'b1': False,
            'b2': True,
            'integer': 3,
            'float': 0.25,
            'json1': [1, 2, 'abc'],
            'json2': {'hello': 'world'},
            'timestamp': datetime.datetime(2017, 1, 1, 11, 35, 22),
            'datestamp': datetime.date(2017, 2, 2)
        })

        # Test request body
        body = 'torso'
        resp = self.request('/auto_describe/body', method='POST',
                            body=json.dumps(body), type='application/json')
        self.assertStatusOk(resp)
        self.assertEqual(len(testRuns), 1)
        self.assertTrue('body' in testRuns[0])
        self.assertTrue(hasattr(testRuns[0]['body'], 'read'))
        del testRuns[-1]

        # Test request JSON body (optional)
        body = {
            'emmet': 'otter'
        }
        resp = self.request('/auto_describe/json_body', method='POST',
                            body=json.dumps(body), type='application/json')
        self.assertStatusOk(resp)
        self.assertEqual(len(testRuns), 1)
        expected = {
            'json_body': body
        }
        self.assertEqual(testRuns[0], expected)
        del testRuns[-1]

        # Test request JSON body (optional), omitting body
        resp = self.request('/auto_describe/json_body', method='POST')
        self.assertStatusOk(resp)
        self.assertEqual(len(testRuns), 1)
        expected = {
            'json_body': None
        }
        self.assertEqual(testRuns[0], expected)
        del testRuns[-1]

        # Test request JSON body (required)
        body = {
            'emmet': 'otter'
        }
        resp = self.request('/auto_describe/json_body_required', method='POST',
                            body=json.dumps(body), type='application/json')
        self.assertStatusOk(resp)
        self.assertEqual(len(testRuns), 1)
        expected = {
            'json_body': body
        }
        self.assertEqual(testRuns[0], expected)
        del testRuns[-1]

        # Test request JSON body (required), omitting body
        resp = self.request('/auto_describe/json_body_required', method='POST')
        self.assertStatus(resp, 400)

        # Test request JSON body (required), pass list
        body = [{
            'emmet': 'otter'
        }]
        resp = self.request('/auto_describe/json_body_required', method='POST',
                            body=json.dumps(body), type='application/json')
        self.assertStatus(resp, 400)

        # Test omission of required modelParam
        resp = self.request('/auto_describe/model_param_query')
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Parameter "userId" is required.')

        resp = self.request('/auto_describe/model_param_query', params={'userId': None})
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Invalid ObjectId: None')

        user = User().createUser(
            firstName='admin', lastName='admin', email='a@admin.com', login='admin',
            password='password')
        resp = self.request(
            '/auto_describe/model_param_query', user=user, params={'userId': user['_id']})
        self.assertStatusOk(resp)

        # Test requiredFlags in modelParam
        resp = self.request('/auto_describe/model_param_flags', params={
            'userId': user['_id']
        })
        self.assertStatus(resp, 401)
        self.assertRegex(resp.json['message'], '^Access denied for user')

        resp = self.request('/auto_describe/json_schema', params={
            'obj': json.dumps([])
        })
        self.assertStatus(resp, 400)
        self.assertRegex(
            resp.json['message'],
            r"^Invalid JSON object for parameter obj: \[\] is not of type 'object'")

        resp = self.request('/auto_describe/json_schema', params={
            'obj': json.dumps({})
        })
        self.assertStatus(resp, 400)
        self.assertRegex(
            resp.json['message'],
            r"^Invalid JSON object for parameter obj: 'foo' is a required property")

        obj = {
            'foo': 1,
            'bar': 2
        }
        resp = self.request('/auto_describe/json_schema', params={
            'obj': json.dumps(obj)
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, obj)

        # Test missing arg in wrapped function, should fall through to params dict
        resp = self.request('/auto_describe/missing_arg', params={
            'foo': 'bar'
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, {'foo': 'bar'})

    def testDeprecatedRoute(self):
        """
        Test that a route marked as deprecated is described as deprecated.
        """
        class OldResource(Resource):
            def __init__(self):
                super().__init__()
                self.resourceName = 'old_resource'
                self.route('GET', (), self.handler)
                self.route('GET', ('deprecated',), self.deprecatedHandler)

            @access.public
            @describe.describeRoute(
                describe.Description('Handler')
            )
            def handler(self, params):
                return None

            @access.public
            @describe.describeRoute(
                describe.Description('Deprecated handler')
                .deprecated()
            )
            def deprecatedHandler(self, params):
                return None

        server.root.api.v1.old_resource = OldResource()

        resp = self.request(path='/describe', method='GET')
        self.assertStatusOk(resp)
        self.assertIn('paths', resp.json)
        self.assertIn('/old_resource', resp.json['paths'])
        self.assertIn('/old_resource/deprecated', resp.json['paths'])
        self.assertIn('get', resp.json['paths']['/old_resource'])
        self.assertNotIn('deprecated', resp.json['paths']['/old_resource']['get'])
        self.assertIn('get', resp.json['paths']['/old_resource/deprecated'])
        self.assertIn('deprecated', resp.json['paths']['/old_resource/deprecated']['get'])
        self.assertTrue(resp.json['paths']['/old_resource/deprecated']['get']['deprecated'])

    def testProduces(self):
        """
        Test that a route marked as producing a list of mime types reports
        that information properly.
        """
        class ProducesResource(Resource):
            def __init__(self):
                super().__init__()
                self.resourceName = 'produces_resource'
                self.route('GET', (), self.handler)
                self.route('GET', ('produces1',), self.producesHandler)
                self.route('GET', ('produces2',), self.produces2Handler)

            @access.public
            @describe.describeRoute(
                describe.Description('Handler')
            )
            def handler(self, params):
                return None

            @access.public
            @describe.describeRoute(
                describe.Description('Produces handler')
                .produces('image/jpeg')
            )
            def producesHandler(self, params):
                return None

            @access.public
            @describe.describeRoute(
                describe.Description('Produces 2 handler')
                .produces('image/tiff')
                .produces(['image/jpeg', 'image/png'])
            )
            def produces2Handler(self, params):
                return None

        server.root.api.v1.produces_resource = ProducesResource()

        resp = self.request(path='/describe', method='GET')
        self.assertStatusOk(resp)
        self.assertIn('paths', resp.json)
        self.assertIn('/produces_resource', resp.json['paths'])
        self.assertIn('/produces_resource/produces1', resp.json['paths'])
        self.assertIn('/produces_resource/produces2', resp.json['paths'])
        self.assertNotIn('produces', resp.json['paths']['/produces_resource']['get'])
        self.assertIn('produces', resp.json['paths']['/produces_resource/produces1']['get'])
        self.assertEqual(resp.json['paths']['/produces_resource/produces1']['get']['produces'],
                         ['image/jpeg'])
        self.assertEqual(resp.json['paths']['/produces_resource/produces2']['get']['produces'],
                         ['image/tiff', 'image/jpeg', 'image/png'])
