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

import mock
import six
import time
import unittest

from girder import events


class EventsTestCase(unittest.TestCase):
    """
    This test case is just a unit test of the girder.events system. It does not
    require the server to be running, or any use of the database.
    """

    def setUp(self):
        self.ctr = 0
        self.responses = None

    def _raiseException(self, event):
        raise Exception('Failure condition')

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
        name, failname = '_test.event', '_test.failure'
        handlerName = '_test.handler'
        with events.bound(name, handlerName, self._increment), \
                events.bound(failname, handlerName, self._raiseException):
            # Make sure our exception propagates out of the handler
            try:
                events.trigger(failname)
                self.assertTrue(False)
            except Exception as e:
                self.assertEqual(e.args[0], 'Failure condition')

            # Bind an event to increment the counter
            self.assertEqual(self.ctr, 0)
            event = events.trigger(name, {'amount': 2})
            self.assertEqual(self.ctr, 2)
            self.assertTrue(event.propagate)
            self.assertFalse(event.defaultPrevented)
            self.assertEqual(event.responses, [])

            # The event should still be bound here if another handler unbinds
            events.unbind(name, 'not the handler name')
            events.trigger(name, {'amount': 2})
            self.assertEqual(self.ctr, 4)

        # Actually unbind the event, by going out of scope of "bound"
        events.trigger(name, {'amount': 2})
        self.assertEqual(self.ctr, 4)

        # Bind an event that prevents the default action and passes a response
        with events.bound(name, handlerName, self._eatEvent), \
                events.bound(name, 'other handler name',
                             self._shouldNotBeCalled):
            event = events.trigger(name)
            self.assertTrue(event.defaultPrevented)
            self.assertFalse(event.propagate)
            self.assertEqual(event.responses, [{'foo': 'bar'}])

        # Test that the context manager unbinds after an unhandled exception
        try:
            with events.bound(failname, handlerName, self._raiseException):
                events.trigger(failname)
        except Exception:
            # The event should should be unbound at this point
            events.trigger(failname)

    def testAsyncEvents(self):
        name, failname = '_test.event', '_test.failure'
        handlerName = '_test.handler'

        def callback(event):
            self.ctr += 1
            self.responses = event.responses

        with events.bound(failname, handlerName, self._raiseException), \
                events.bound(name, handlerName, self._incrementWithResponse):
            # Make sure an async handler that fails does not break the event
            # loop and that its callback is not triggered.
            self.assertEqual(events.daemon.eventQueue.qsize(), 0)
            events.daemon.trigger(failname, handlerName, callback)

            # Triggering the event before the daemon starts should do nothing
            self.assertEqual(events.daemon.eventQueue.qsize(), 1)
            events.daemon.trigger(name, {'amount': 2}, callback)
            self.assertEqual(events.daemon.eventQueue.qsize(), 2)
            self.assertEqual(self.ctr, 0)

            # Now run the asynchronous event handler, which should eventually
            # cause our counter to be incremented.
            events.daemon.start()
            # Ensure that all of our events have been started within a
            # reasonable amount of time.  Also check the results in the loop,
            # since the qsize only indicates if all events were started, not
            # finished.
            startTime = time.time()
            while True:
                if events.daemon.eventQueue.qsize() == 0:
                    if self.ctr == 3:
                        break
                if time.time() - startTime > 15:
                    break
                time.sleep(0.1)
            self.assertEqual(events.daemon.eventQueue.qsize(), 0)
            self.assertEqual(self.ctr, 3)
            self.assertEqual(self.responses, ['foo'])
            events.daemon.stop()

    @mock.patch.object(events, 'daemon', new=events.ForegroundEventsDaemon())
    def testForegroundDaemon(self):
        self.assertIsInstance(events.daemon, events.ForegroundEventsDaemon)

        # Should still be able to call start
        events.daemon.start()

        def callback(event):
            self.ctr += 1
            self.responses = event.responses

        with events.bound('_test.event',  '_test.handler', self._raiseException):
            with six.assertRaisesRegex(self, Exception, 'Failure condition'):
                events.daemon.trigger('_test.event', None, callback)

        with events.bound('_test.event',  '_test.handler', self._incrementWithResponse):
            events.daemon.trigger('_test.event', {'amount': 2}, callback)

        self.assertEqual(self.ctr, 3)
        self.assertEqual(self.responses, ['foo'])

        events.daemon.stop()
