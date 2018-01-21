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
import celery

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.constants import TokenScope
from girder.api.rest import Resource

from ..celery import getCeleryApp


class Worker(Resource):
    def __init__(self):
        super(Worker, self).__init__()
        self.resourceName = 'worker'
        self.route('GET', ('status',), self.getWorkerStatus)

    @autoDescribeRoute(
        Description('Get worker status and task information.')
        .notes('Return -1 if the broker is inaccessible.')
    )
    @access.user(scope=TokenScope.DATA_READ)
    def getWorkerStatus(self):
        app = getCeleryApp()
        result = {}
        conn = app.connection_for_read()
        try:
            conn.ensure_connection(max_retries=1)
        except celery.exceptions.OperationalError:
            return -1

        status = app.control.inspect()
        result['report'] = status.report()
        result['stats'] = status.stats()
        result['ping'] = status.ping()
        result['active'] = status.active()
        result['reserved'] = status.reserved()
        return result
