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

import time
import unittest

from girder import events


class EventsTestCase(unittest.TestCase):
    """
    This test case is just a unit test of the girder.events system. It does not
    require the server to be running, or any use of the database.
    """

    def setUp(self):
        events.unbindAll()
        self.ctr = 0

    def _increment(self, event):
        self.ctr += event.info['amount']

    def _incrementWithResponse(self, event):
        self._increment(event)
        event.addResponse('foo')

    def _eatEvent(self, event):
        event.addResponse({'foo': 'bar'})
        event.stopPropagation()
        event.preventDefault()

    def _shouldNotBeCalled(self, event):
        self.fail('This should not be called due to stopPropagation().')

    def testSynchronousEvents(self):
        name = '_test.event'
        handlerName = '_test.handler'
        events.bind(name, handlerName, self._increment)

        # Bind an event to increment the counter
        self.assertEqual(self.ctr, 0)
        event = events.trigger(name, {'amount': 2})
        self.assertEqual(self.ctr, 2)
        self.assertTrue(event.propagate)
        self.assertFalse(event.defaultPrevented)
        self.assertEqual(event.responses, [])

        # The event should still be bound here if a different handler unbinds
        events.unbind(name, 'not the handler name')
        events.trigger(name, {'amount': 2})
        self.assertEqual(self.ctr, 4)

        # Actually unbind the event, it show now no longer execute
        events.unbind(name, handlerName)
        events.trigger(name, {'amount': 2})
        self.assertEqual(self.ctr, 4)

        # Bind an event that prevents the default action and passes a response
        events.bind(name, handlerName, self._eatEvent)
        events.bind(name, 'other handler name', self._shouldNotBeCalled)
        event = events.trigger(name)
        self.assertTrue(event.defaultPrevented)
        self.assertFalse(event.propagate)
        self.assertEqual(event.responses, [{'foo': 'bar'}])

    def testAsyncEvents(self):
        name = '_test.event'
        handlerName = '_test.handler'
        events.bind(name, handlerName, self._incrementWithResponse)

        def callback(event):
            self.ctr += 1
            self.assertEqual(event.responses, {handlerName: 'foo'})

        # Triggering the event before the daemon starts should do nothing
        self.assertEqual(events.daemon.eventQueue.qsize(), 0)
        events.daemon.trigger(name, {'amount': 2}, callback)
        self.assertEqual(events.daemon.eventQueue.qsize(), 1)
        self.assertEqual(self.ctr, 0)

        # Now run the asynchronous event handler, which should eventually
        # cause our counter to be incremented.
        events.daemon.start()
        time.sleep(0.1)
        self.assertEqual(events.daemon.eventQueue.qsize(), 0)
        self.assertEqual(self.ctr, 3)
