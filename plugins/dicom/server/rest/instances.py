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

from error_descriptions import describe_qidors_errors
from param_descriptions import *


class dicomInstances(Resource):
    def __init__(self):
        self.resourceName = 'instances'

        ###########
        # QIDO-RS #
        ###########

        # {+SERVICE}/instances{?query*,fuzzymatching,limit,offset}
        self.route('GET', (), self.searchForInstances)

    ###########
    # QIDO-RS #
    ###########

    @access.user
    def searchForInstances(self, params):
        pass

    searchForInstances.description = (
        Description(SearchForDescription % ('Instances', 'instances', 'instance'))
        .param('query', QueryParamDescription,
               required=False)
        .param('fuzzymatching', FuzzyMatchingParamDescription,
               required=False, dataType='boolean', default=False)
        .param('limit', LimitParamDescription,
               required=False, dataType='integer')
        .param('offset', OffsetParamDescription,
               required=False, dataType='integer', default=0))
    searchForInstances.description = describe_qidors_errors(searchForInstances)

