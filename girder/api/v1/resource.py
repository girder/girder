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

import cherrypy
import json
import os
import pymongo

from .docs import folder_docs
from ..rest import Resource as BaseResource, RestException
from ...constants import AccessType
from ...utility import ziputil


class Resource(BaseResource):
    """API Endpoint for folders."""

    def search(self, user, params):
        return []

    @BaseResource.endpoint
    def GET(self, path, params):
        user = self.getCurrentUser()
        if not path:
            raise RestException('Unsupported operation.')
        elif path[0] == 'search':
            return self.search(user, params)
        else:
            raise RestException('Unsupported operation.')
