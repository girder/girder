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

# import time
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.constants import TokenScope
from girder.api.rest import Resource
from ..utils import getCeleryApp


class Worker(Resource):
    def __init__(self):
        super(Worker, self).__init__()
        self.resourceName = 'worker'
        self.route('GET', ('status',), self.getWorkerStatus)
        # self.route('GET', ('task',), self.callTask)
        # self.route('GET', ('task','info'), self.infoTask)

    @autoDescribeRoute(
        Description('Get workers status.')
        .notes('Note')
    )
    @access.user(scope=TokenScope.DATA_READ)
    def getWorkerStatus(self):
        app = getCeleryApp()
        result = {}
        status = app.control.inspect()
        result['report'] = status.report()
        result['stats'] = status.stats()
        return result

    # @autoDescribeRoute(
    #     Description('Get workers status.')
    #     .notes('Note')
    #     .param('a', 'first nb')
    #     .param('b', 'second nb')
    # )
    # @access.user(scope=TokenScope.DATA_READ)
    # def callTask(self, a, b):
    #     app = getCeleryApp()
    #
    #     @app.task
    #     def add(x, y):
    #         time.sleep(30)
    #         return x + y
    #
    #     result = add.delay(a, b)
    #     return result.ready()
    #
    # @autoDescribeRoute(
    #     Description('Get workers status.')
    # )
    # @access.user(scope=TokenScope.DATA_READ)
    # def infoTask(self):
    #     from celery.task.control import inspect
    #
    #     i = inspect()
    #
    #     return {
    #         'scheduled': i.scheduled(),
    #         'active': i.active(),
    #         'reserved': i.reserved()
    #     }
