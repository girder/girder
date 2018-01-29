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
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, Prefix


class Resourceful(Resource):
    def __init__(self):
        super(Resourceful, self).__init__()

        self.route('GET', (), self.getResource, resource=self)

    @access.public
    @describeRoute(
        Description('Get something.')
    )
    def getResource(self, params):
        return ['custom REST route']


def load(info):
    info['apiRoot'].prefix = Prefix()
    info['apiRoot'].prefix.resourceful = Resourceful()
    info['apiRoot'].prefix.sibling = Resourceful()
