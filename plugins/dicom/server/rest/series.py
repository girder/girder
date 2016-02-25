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

from girder.api.describe import Description
from girder.api.rest import Resource
from girder.api import access

from error_descriptions import _describe_qidors_errors
from param_descriptions import *


class dicomSeries(Resource):
    def __init__(self):
        self.resourceName = 'series'

        ###########
        # QIDO-RS #
        ###########

        # {+SERVICE}/series{?query*,fuzzymatching,limit,offset}
        self.route('GET', (), self.searchForSeries)

    ###########
    # QIDO-RS #
    ###########

    @access.user
    def searchForSeries(self, params):
        pass

    searchForSeries.description = (
        Description(SearchForDescription % ('Series', 'series', 'series'))
        .param('query', QueryParamDescription,
               required=False)
        .param('fuzzymatching', FuzzyMatchingParamDescription,
               required=False, dataType='boolean', default=False)
        .param('limit', LimitParamDescription,
               required=False, dataType='integer')
        .param('offset', OffsetParamDescription,
               required=False, dataType='integer', default=0))
    searchForSeries.description = _describe_qidors_errors(searchForSeries)
