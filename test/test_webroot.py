# -*- coding: utf-8 -*-
import cherrypy

from girder.models.setting import Setting
from girder.settings import SettingKey
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


def testAccessWebRoot(server):
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


def testWebRootProperlyHandlesCustomStaticPublicPath(server):
    cherrypy.config['server']['static_public_path'] = 'http://my-cdn-url.com/static'

    resp = server.request(path='/', method='GET', isJson=False, prefix='')
    assertStatusOk(resp)
    body = getResponseBody(resp)

    assert 'href="http://my-cdn-url.com/static/built/Girder_Favicon.png"' in body

    # Same assertion should hold true for Swagger
    resp = server.request(path='/', method='GET', isJson=False)
    assertStatusOk(resp)
    body = getResponseBody(resp)

    assert 'href="http://my-cdn-url.com/static/built/Girder_Favicon.png"' in body

    cherrypy.config['server']['static_public_path'] = '/static'


def testWebRootTemplateFilename():
    """
    Test WebrootBase.templateFilename attribute after initialization
    and after setting a custom template path.
    """
    webroot = WebrootBase(templatePath='/girder/base_template.mako')
    assert webroot.templateFilename == 'base_template.mako'

    webroot.setTemplatePath('/plugin/custom_template.mako')
    assert webroot.templateFilename == 'custom_template.mako'
