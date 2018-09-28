#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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

import os

import pytest
from pytest_girder.assertions import assertStatusOk
from pytest_girder.utils import getResponseBody

from girder.plugin import GirderPlugin


class CustomAPIDocs(GirderPlugin):
    def load(self, info):
        info['apiRoot'].updateHtmlVars({
            'baseTemplateFilename': info['apiRoot'].templateFilename
        })

        templatePath = os.path.join(os.path.dirname(__file__), 'data', 'custom_api_docs.mako')
        info['apiRoot'].setTemplatePath(templatePath)


def testApiDocsContent(server):
    """
    Test content of API documentation page.
    """
    resp = server.request(path='/api/v1', method='GET', isJson=False, prefix='')
    assertStatusOk(resp)
    body = getResponseBody(resp)

    assert 'Girder REST API Documentation' in body
    assert 'This is not a sandbox' in body
    assert 'id="swagger-ui-container"' in body


@pytest.mark.plugin('custom_api_docs', CustomAPIDocs)
def testApiDocsCustomContent(server):
    """
    Test content of API documentation page that's customized by a plugin.
    """
    resp = server.request(path='/api/v1', method='GET', isJson=False, prefix='')
    assertStatusOk(resp)
    body = getResponseBody(resp)

    assert 'Girder REST API Documentation' not in body
    assert 'This is not a sandbox' not in body

    assert 'Girder Web Application Programming Interface' in body
    assert '<p>Custom API description</p>' in body
    assert 'id="swagger-ui-container"' in body
