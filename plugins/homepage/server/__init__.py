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

from girder import events
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource

KEY = 'homepage.markdown'


class Homepage(Resource):
    def __init__(self):
        super(Homepage, self).__init__()
        self.resourceName = 'homepage'
        self.route('GET', ('markdown',), self.getMarkdown)

    @access.public
    @describeRoute(
        Description('Public url for getting the homepage markdown.')
    )
    def getMarkdown(self, params):
        return {KEY: self.model('setting').get(KEY)}


def validateSettings(event):
    if event.info['key'] == KEY:
        event.preventDefault().stopPropagation()


def load(info):
    events.bind('model.setting.validate', 'homepage', validateSettings)
    info['apiRoot'].homepage = Homepage()
