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

from ..describe import Description, describeRoute
from ..rest import Resource, setResponseHeader
from girder.api import access

# If no timeout param is passed to stream, we default to this value
DEFAULT_STREAM_TIMEOUT = 300
# When new events are seen, we will poll at the minimum interval
MIN_POLL_INTERVAL = 0.5
# The interval increases when no new events are seen, capping at this value
MAX_POLL_INTERVAL = 2


def sseMessage(event):
    """
    Serializes an event into the server-sent events protocol.
    """
    return 'data: %s\n\n' % json.dumps(event, default=str)


class Notification(Resource):
    def __init__(self):
        super(Notification, self).__init__()
        self.resourceName = 'notification'
        self.route('GET', ('stream',), self.stream)

    @access.cookie
    @access.token
    @describeRoute(
        Description('Stream notifications for a given user via the SSE '
                    'protocol.')
        .notes('This uses long-polling to keep the connection open for '
               'several minutes at a time (or longer) and should be requested '
               'with an EventSource object or other SSE-capable client. '
               '<p>Notifications are returned within a few seconds of when '
               'they occur.  When no notification occurs for the timeout '
               'duration, the stream is closed. '
               '<p>This connection can stay open indefinitely long.')
        .param('timeout', 'The duration without a notification before the '
               'stream is closed.', dataType='integer', required=False)
        .errorResponse()
        .errorResponse('You are not logged in.', 403)
    )
    def stream(self, params):
        """
        Streams notifications using the server-sent events protocol. Closes
        the connection if more than timeout seconds elapse without any new
        notifications.

        :params timeout: Timeout in seconds; if no notifications appear in
            this duration, the connection will be closed. (default=300)
        :type timeout: int
        """
        user = self.getCurrentUser()
        token = self.getCurrentToken()

        setResponseHeader('Content-Type', 'text/event-stream')
        setResponseHeader('Cache-Control', 'no-cache')

        timeout = int(params.get('timeout', DEFAULT_STREAM_TIMEOUT))

        def streamGen():
            lastUpdate = None
            start = time.time()
            wait = MIN_POLL_INTERVAL
            while cherrypy.engine.state == cherrypy.engine.states.STARTED:
                wait = min(wait + MIN_POLL_INTERVAL, MAX_POLL_INTERVAL)
                for event in self.model('notification').get(
                        user, lastUpdate, token=token):
                    if lastUpdate is None or event['updated'] > lastUpdate:
                        lastUpdate = event['updated']
                    wait = MIN_POLL_INTERVAL
                    start = time.time()
                    yield sseMessage(event)
                if time.time() - start > timeout:
                    break

                time.sleep(wait)
        return streamGen
