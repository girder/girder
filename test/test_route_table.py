# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2016 Kitware Inc.
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

import pytest
from pytest_girder.assertions import assertStatusOk
from pytest_girder.utils import getResponseBody

from girder.constants import GIRDER_ROUTE_ID, SettingKey
from girder.exceptions import ValidationException
from girder.models.setting import Setting
from girder.plugin import GirderPlugin, registerPluginWebroot


class SomeWebroot(object):
    exposed = True

    def GET(self):
        return "some webroot"


class HasWebroot(GirderPlugin):
    def load(self, info):
        registerPluginWebroot(SomeWebroot(), 'has_webroot')


@pytest.mark.parametrize('value,err', [
    ({}, r'Girder root must be routable\.$'),
    ({'other': '/some_route'}, r'Girder root must be routable\.$'),
    ({
        GIRDER_ROUTE_ID: '/some_route',
        'other': '/some_route'
    }, r'Routes must be unique\.$'),
    ({
        GIRDER_ROUTE_ID: '/',
        'other': 'route_without_a_leading_slash'
    }, r'Routes must begin with a forward slash\.$')
])
def testRouteTableValidationFailure(value, err):
    with pytest.raises(ValidationException, match=err):
        Setting().validate({
            'key': SettingKey.ROUTE_TABLE,
            'value': value
        })


@pytest.mark.parametrize('value', [
    {
        GIRDER_ROUTE_ID: '/',
    }
])
def testRouteTableValidationSuccess(value):
    Setting().validate({
        'key': SettingKey.ROUTE_TABLE,
        'value': value
    })


@pytest.mark.plugin('has_webroot', HasWebroot)
def testRouteTableBehavior(server, admin):
    Setting().set(SettingKey.ROUTE_TABLE, {
        GIRDER_ROUTE_ID: '/',
        'has_webroot': '/has_webroot'
    })

    # /has_webroot should serve our plugin webroot
    resp = server.request('/has_webroot', prefix='', isJson=False, appPrefix='/has_webroot')
    assertStatusOk(resp)
    assert 'some webroot' in getResponseBody(resp)

    # girder should be at /
    resp = server.request('/', prefix='', isJson=False)
    assertStatusOk(resp)
    assert 'g-global-info-apiroot' in getResponseBody(resp)

    table = Setting().get(SettingKey.ROUTE_TABLE)
    assert 'has_webroot' in table
    assert table['has_webroot'] == '/has_webroot'
