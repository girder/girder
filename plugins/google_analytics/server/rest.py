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

from . import constants
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource
from girder.models.setting import Setting


class GoogleAnalytics(Resource):
    def __init__(self):
        super(GoogleAnalytics, self).__init__()
        self.resourceName = 'google_analytics'
        self.route('GET', ('id',), self.getId)

    @access.public
    @describeRoute(
        Description('Public url for getting the Google Analytics tracking id.')
    )
    def getId(self, params):
        trackingId = Setting().get(constants.PluginSettings.GOOGLE_ANALYTICS_TRACKING_ID)
        return {'google_analytics_id': trackingId}
