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

from ..rest import Resource

class ApiDocs(object):
    exposed = True

    def GET(self):
        # TODO swagger
        return "should display version 1 api docs"

class Version(Resource):
    """
    This endpoint will output the current semantic version of the API.
    Whenever we add new return values or new options we should increment the maintenance
    value. Whenever we add new endpoints, we should increment the minor version. If we break
    backward compatibility in any way, we should increment the major version.
    """
    exposed = True

    @Resource.endpoint
    def GET(self, path, params):
        return {'version': '1.0.0'}
