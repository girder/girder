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

from girder.api import access
from girder.api.describe import Description
from girder.api.rest import Resource


class CustomAppRoot(object):
    """
    The webroot endpoint simply serves the main index HTML file.
    """
    exposed = True

    def GET(self):
        return "hello world"


class Other(Resource):
    def __init__(self):
        self.resourceName = 'other'

        self.route('GET', (), self.getResource)

    @access.public
    def getResource(self, params):
        return ['custom REST route']
    getResource.description = Description('Get something.')


def load(info):
    info['serverRoot'], info['serverRoot'].girder = (
        CustomAppRoot(), info['serverRoot'])
    info['serverRoot'].api = info['serverRoot'].girder.api
    del info['serverRoot'].girder.api

    info['apiRoot'].other = Other()
