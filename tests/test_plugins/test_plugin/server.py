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

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import boundHandler, rawResponse, Resource, setResponseHeader
from girder.api.v1.collection import Collection
from girder.constants import TokenScope
from girder.utility.server import staticFile


@access.user(scope=TokenScope.ANONYMOUS_SESSION)
@boundHandler
@describeRoute(None)
def unboundHandlerDefaultNoArgs(self, params):
    self.requireParams('val', params)
    return not self.boolParam('val', params)


@access.user(scope=TokenScope.ANONYMOUS_SESSION)
@boundHandler()
@describeRoute(None)
def unboundHandlerDefault(self, params):
    self.requireParams('val', params)
    return not self.boolParam('val', params)


@access.user(scope=TokenScope.ANONYMOUS_SESSION)
@boundHandler(Collection())
@describeRoute(None)
def unboundHandlerExplicit(self, params):
    currentUser = self.getCurrentUser()
    return {
        'userLogin': currentUser['login'] if currentUser else None,
        'name': self.resourceName
    }


class CustomAppRoot(object):
    """
    The webroot endpoint simply serves the main index HTML file.
    """
    exposed = True

    def GET(self):
        return "hello world from test_plugin"


class Other(Resource):
    def __init__(self):
        super(Other, self).__init__()
        self.resourceName = 'other'

        self.route('GET', (), self.getResource)
        self.route('GET', ('rawWithDecorator',), self.rawWithDecorator)
        self.route('GET', ('rawReturningText',), self.rawReturningText)
        self.route('GET', ('rawInternal',), self.rawInternal)

    @access.public
    @rawResponse
    @describeRoute(None)
    def rawWithDecorator(self, params):
        return b'this is a raw response'

    @access.public
    @rawResponse
    @describeRoute(None)
    def rawReturningText(self, params):
        setResponseHeader('Content-Type', 'text/plain')
        return u'this is not encoded \U0001F44D'

    @access.public
    @describeRoute(None)
    def rawInternal(self, params):
        self.setRawResponse()
        return b'this is also a raw response'

    @access.public
    @describeRoute(
        Description('Get something.')
    )
    def getResource(self, params):
        return ['custom REST route']


def load(info):
    info['serverRoot'], info['serverRoot'].girder = (
        CustomAppRoot(), info['serverRoot'])
    info['serverRoot'].api = info['serverRoot'].girder.api
    del info['serverRoot'].girder.api

    info['apiRoot'].collection.route('GET', ('unbound', 'default', 'noargs'),
                                     unboundHandlerDefaultNoArgs)
    info['apiRoot'].collection.route('GET', ('unbound', 'default'),
                                     unboundHandlerDefault)
    info['apiRoot'].collection.route('GET', ('unbound', 'explicit'),
                                     unboundHandlerExplicit)

    info['apiRoot'].other = Other()
    path = os.path.join(globals()['PLUGIN_ROOT_DIR'], 'static.txt')
    info['serverRoot'].static_route = staticFile(path)
