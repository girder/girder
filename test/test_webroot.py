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

from girder.constants import GIRDER_ROUTE_ID, GIRDER_STATIC_ROUTE_ID, SettingKey
from girder.models.setting import Setting
from pytest_girder.assertions import assertStatusOk
from pytest_girder.utils import getResponseBody
from girder.utility.webroot import WebrootBase


def testEscapeJavascript():
    # Don't escape alphanumeric characters
    alphaNumString = 'abcxyz0189ABCXYZ'
    assert WebrootBase._escapeJavascript(alphaNumString) == alphaNumString

    # Do escape everything else
    dangerString = 'ab\'"<;>\\YZ'
    assert WebrootBase._escapeJavascript(dangerString) == \
        'ab\\u0027\\u0022\\u003C\\u003B\\u003E\\u005CYZ'


def testAccessWebRoot(server, db):
    """
    Requests the webroot and tests the existence of several
    elements in the returned html
    """
    # Check webroot default settings
    defaultEmailAddress = Setting().getDefault(SettingKey.CONTACT_EMAIL_ADDRESS)
    defaultBrandName = Setting().getDefault(SettingKey.BRAND_NAME)
    resp = server.request(path='/', method='GET', isJson=False, prefix='')
    assertStatusOk(resp)
    body = getResponseBody(resp)
    assert WebrootBase._escapeJavascript(defaultEmailAddress) in body
    assert '<title>%s</title>' % defaultBrandName in body

    assert 'girder_app.min.js' in body
    assert 'girder_lib.min.js' in body

    # Change webroot settings
    Setting().set(SettingKey.CONTACT_EMAIL_ADDRESS, 'foo@bar.com')
    Setting().set(SettingKey.BRAND_NAME, 'FooBar')
    resp = server.request(path='/', method='GET', isJson=False, prefix='')
    assertStatusOk(resp)
    body = getResponseBody(resp)
    assert WebrootBase._escapeJavascript('foo@bar.com') in body
    assert '<title>FooBar</title>' in body

    # Remove webroot settings
    Setting().unset(SettingKey.CONTACT_EMAIL_ADDRESS)
    Setting().unset(SettingKey.BRAND_NAME)
    resp = server.request(path='/', method='GET', isJson=False, prefix='')
    assertStatusOk(resp)
    body = getResponseBody(resp)
    assert WebrootBase._escapeJavascript(defaultEmailAddress) in body
    assert '<title>%s</title>' % defaultBrandName in body


def testWebRootProperlyHandlesStaticRouteUrls(server, db):
    Setting().set(SettingKey.ROUTE_TABLE, {
        GIRDER_ROUTE_ID: '/',
        GIRDER_STATIC_ROUTE_ID: 'http://my-cdn-url.com/static'
    })

    resp = server.request(path='/', method='GET', isJson=False, prefix='')
    assertStatusOk(resp)
    body = getResponseBody(resp)

    assert 'href="http://my-cdn-url.com/static/img/Girder_Favicon.png"' in body

    # Same assertion should hold true for Swagger
    resp = server.request(path='/', method='GET', isJson=False)
    assertStatusOk(resp)
    body = getResponseBody(resp)

    assert 'href="http://my-cdn-url.com/static/img/Girder_Favicon.png"' in body

def testWebRootTemplateFilename():
    """
    Test WebrootBase.templateFilename attribute after initialization
    and after setting a custom template path.
    """
    webroot = WebrootBase(templatePath='/girder/base_template.mako')
    assert webroot.templateFilename == 'base_template.mako'

    webroot.setTemplatePath('/plugin/custom_template.mako')
    assert webroot.templateFilename == 'custom_template.mako'
