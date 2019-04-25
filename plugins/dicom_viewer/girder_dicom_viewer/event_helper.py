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

import threading

from girder import events


class _EventHelper(object):
    """
    Helper class to wait for plugin's data.process event handler to complete.
    Usage:
        with EventHelper('event.name') as helper:
            Upload().uploadFile(...)
            handled = helper.wait()
    """
    def __init__(self, eventName, timeout=10):
        self.eventName = eventName
        self.timeout = timeout
        self.handlerName = 'HandlerCallback'
        self.event = threading.Event()

    def wait(self):
        """
        Wait for the handler to complete.
        :returns: True if the handler completes before the timeout or has
                  already been called.
        """
        return self.event.wait(self.timeout)

    def _callback(self, event):
        self.event.set()

    def __enter__(self):
        events.bind(self.eventName, self.handlerName, self._callback)
        return self

    def __exit__(self, *args):
        events.unbind(self.eventName, self.handlerName)
