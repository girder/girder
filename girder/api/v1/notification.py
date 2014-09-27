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
import time

from ..describe import Description
from ..rest import Resource
from girder.models.model_base import AccessException
from girder.utility.progress import ProgressContext
from girder.api import access


def sseMessage(event):
    """
    Serializes an event into the server-sent events protocol.
    """
    return 'data: {}\n\n'.format(json.dumps(event, default=str))


class Notification(Resource):
    def __init__(self):
        self.resourceName = 'notification'
        self.route('GET', ('stream',), self.stream)
        self.route('GET', ('test',), self.test)

    @access.user
    def stream(self, params):
        """
        Streams notifications using the server-sent events protocol. Closes
        the connection if more than timeout seconds elapse without any new
        notifications.

        :params timeout: Timeout in seconds; if no notifications appear in
        this window, the connection will be closed. (default=300)
        :type timeout: int
        """
        user = self.getCurrentUser()

        cherrypy.response.headers['Content-Type'] = 'text/event-stream'
        cherrypy.response.headers['Cache-Control'] = 'no-cache'

        timeout = int(params.get('timeout', 300))

        def streamGen():
            lastUpdate = None
            start = time.time()
            wait = 0.5
            while time.time() - start < timeout and\
                    cherrypy.engine.state == cherrypy.engine.states.STARTED:
                wait = min(wait + 0.5, 3)
                for event in self.model('notification').get(user, lastUpdate):
                    if lastUpdate is None or event['updated'] > lastUpdate:
                        lastUpdate = event['updated']
                    wait = 0.5
                    start = time.time()
                    yield sseMessage(event)

                time.sleep(wait)
        return streamGen
    stream.description = None

    def test(self, params):
        with ProgressContext(True, user=self.getCurrentUser(), title='Test!',
                             total=100) as p:
            for i in xrange(100):
                p.update(current=i+1)
                time.sleep(1)

    test.description = Description('Test')
