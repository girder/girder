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
import datetime
import json
import time

from ..rest import Resource
from girder.models.model_base import AccessException


def sseMessage(event):
    """
    Serializes an event into the server-sent events protocol
    """
    return 'data: {}\n'.format(json.dumps(event))


class Notification(Resource):
    def __init__(self):
        self.resourceName = 'notification'
        self.route('GET', ('stream',), self.stream)

    def stream(self, params):
        """
        Streams notifications using the server-sent events protocol.
        """
        user = self.getCurrentUser()

        if user is None:
            raise AccessException('You must be logged in to receive '
                                  'notifications.')

        cherrypy.response.headers['Content-Type'] = 'text/event-stream'
        cherrypy.response.headers['Cache-Control'] = 'no-cache'

        def streamGen():
            while True:
                wait = 2
                for event in self.model('notification').get(user):
                    wait = 0.5
                    yield sseMessage(event)

                time.sleep(wait)
        return streamGen
    stream.description = None
