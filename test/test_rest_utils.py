# -*- coding: utf-8 -*-
import datetime
import json
import pytest
import pytz

from girder.api import rest
from girder.exceptions import GirderException
from girder.settings import SettingKey
from girder.models.setting import Setting
import girder.events

date = datetime.datetime.now()


class TestResource:
    @rest.endpoint
    def returnsSet(self, *args, **kwargs):
        return {'key': {1, 2, 3}}

    @rest.endpoint
    def returnsDate(self, *args, **kwargs):
        return {'key': date}

    @rest.endpoint
    def returnsInf(self, *args, **kwargs):
        return {'value': float('inf')}


@pytest.mark.parametrize('input,expected', [
    ('TRUE', True),
    (' true  ', True),
    ('Yes', True),
    ('1', True),
    ('ON', True),
    ('false', False),
    ('False', False),
    ('OFF', False),
    ('', False),
    (' ', False),
    (False, False),
    (True, True)
])
def testBoolParam(input, expected):
    assert rest.Resource().boolParam('some_key', {'some_key': input}) == expected


def testBoolParamDefault():
    assert rest.Resource().boolParam('some_key', {}, default='x') == 'x'


def testGetApiUrl():
    url = 'https://localhost/thing/api/v1/hello/world?foo=bar#test'
    assert rest.getApiUrl(url) == 'https://localhost/thing/api/v1'

    parts = rest.getUrlParts(url)
    assert parts.path == '/thing/api/v1/hello/world'
    assert rest.getApiUrl(parts.path) == '/thing/api/v1'
    assert parts.port is None
    assert parts.hostname == 'localhost'
    assert parts.query == 'foo=bar'
    assert parts.fragment == 'test'

    url = 'https://localhost/girder#users'
    with pytest.raises(GirderException, match='Could not determine API root in %s.$' % url):
        rest.getApiUrl(url)


def testCustomJsonEncoder():
    resource = TestResource()
    resp = resource.returnsSet().decode('utf8')
    assert json.loads(resp) == {'key': [1, 2, 3]}

    resp = resource.returnsDate().decode('utf8')
    assert json.loads(resp) == {'key': date.replace(tzinfo=pytz.UTC).isoformat()}

    # Returning infinity or NaN floats should raise a reasonable exception
    with pytest.raises(ValueError, match='Out of range float values are not JSON compliant'):
        resource.returnsInf()


def testCustomJsonEncoderEvent():
    def _toString(event):
        obj = event.info
        if isinstance(obj, set):
            event.addResponse(str(list(obj)))

    with girder.events.bound('rest.json_encode', 'toString', _toString):
        resource = TestResource()
        resp = resource.returnsSet().decode('utf8')
        assert json.loads(resp) == {'key': '[1, 2, 3]'}
        # Check we still get default encode for date
        resp = resource.returnsDate().decode('utf8')
        assert json.loads(resp) == {'key': date.replace(tzinfo=pytz.UTC).isoformat()}


@pytest.mark.parametrize('params', [
    {'hello': 'world'},
    {'hello': None}
])
def testRequireParamsDictMode(params):
    resource = rest.Resource()
    resource.requireParams('hello', params)


@pytest.mark.parametrize('params', [{'foo': 'bar'}, None])
def testRequireParamsDictModeFailure(params):
    resource = rest.Resource()
    with pytest.raises(rest.RestException, match='Parameter "hello" is required.$'):
        resource.requireParams(['hello'], params)


@pytest.mark.parametrize('name,disp,msg', [
    ('filename', 'unknown', r'Error: Content-Disposition \(.*\) is not a recognized value.$'),
    ('', 'attachment', r'Error: Content-Disposition filename is empty.$')
])
def testSetContentDispositionFails(name, disp, msg):
    with pytest.raises(rest.RestException, match=msg):
        rest.setContentDisposition(name, disp, setHeader=False)


@pytest.mark.parametrize('name,disp,expected', [
    ('filename', None, 'attachment; filename="filename"'),
    ('filename', 'inline', 'inline; filename="filename"'),
    ('filename', 'form-data; name="chunk"', 'form-data; name="chunk"; filename="filename"'),
    ('file "name"', None, 'attachment; filename="file \\"name\\""'),
    ('file\\name', None, 'attachment; filename="file\\\\name"'),
    (u'\u043e\u0431\u0440\u0430\u0437\u0435\u0446', None,
     'attachment; filename=""; filename*=UTF-8\'\'%D0%BE%D0%B1%D1%80%D0%B0%D0%B7%D0%B5%D1%86'),
    (u'\U0001f603', None, 'attachment; filename=""; filename*=UTF-8\'\'%F0%9F%98%83')
])
def testSetContentDisposition(name, disp, expected):
    if disp is None:
        assert rest.setContentDisposition(name, setHeader=False) == expected
    else:
        assert rest.setContentDisposition(name, disp, setHeader=False) == expected


@pytest.mark.parametrize('allowed,origin,expected', [
    ('*', 'thing.com', '*'),
    ('*,thing.com', 'thing.com', 'thing.com'),
    ('thing.com', 'thing.com', 'thing.com'),
    ('thing.com', 'notthing.com', None),
    ('thing.com', 'subdomain.thing.com', None),
    ('*.thing.com', 'subdomain.thing.com', 'subdomain.thing.com'),
    (
        'fixed*more-fixed.thing.com',
        'fixed-something-more-fixed.thing.com',
        'fixed-something-more-fixed.thing.com'
    ),
    ('fixed*more-fixed.thing.com', 'other-fixed*other.thing.com', None),
    ('anything,thing.com,thing,*thing,thing*', 'anything.com', None),
    ('*thing*', 'anything.com', 'anything.com'),
])
def testDynamicCORS(server, allowed, origin, expected):
    Setting().set(SettingKey.CORS_ALLOW_ORIGIN, allowed)

    resp = server.request('/user/me', method='GET', additionalHeaders=[('Origin', origin)])
    assert resp.headers.get('Access-Control-Allow-Origin') == expected
