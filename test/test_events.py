# -*- coding: utf-8 -*-
import pytest
import time
import unittest.mock

from girder import events


class EventsHelper:
    def __init__(self):
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
        pytest.fail('This should not be called due to stopPropagation().')


@pytest.fixture
def eventsHelper():
    yield EventsHelper()


def testSynchronousEvents(eventsHelper):
    name, failname = '_test.event', '_test.failure'
    handlerName = '_test.handler'
    with events.bound(name, handlerName, eventsHelper._increment), \
            events.bound(failname, handlerName, eventsHelper._raiseException):
        # Make sure our exception propagates out of the handler
        with pytest.raises(Exception, match='^Failure condition$'):
            events.trigger(failname)

        # Bind an event to increment the counter
        assert eventsHelper.ctr == 0
        event = events.trigger(name, {'amount': 2})
        assert eventsHelper.ctr == 2
        assert event.propagate
        assert not event.defaultPrevented
        assert event.responses == []

        # The event should still be bound here if another handler unbinds
        events.unbind(name, 'not the handler name')
        events.trigger(name, {'amount': 2})
        assert eventsHelper.ctr == 4

    # Actually unbind the event, by going out of scope of "bound"
    events.trigger(name, {'amount': 2})
    assert eventsHelper.ctr == 4

    # Bind an event that prevents the default action and passes a response
    with events.bound(name, handlerName, eventsHelper._eatEvent), \
            events.bound(name, 'other handler name',
                         eventsHelper._shouldNotBeCalled):
        event = events.trigger(name)
        assert event.defaultPrevented
        assert not event.propagate
        assert event.responses == [{'foo': 'bar'}]

    # Test that the context manager unbinds after an unhandled exception
    try:
        with events.bound(failname, handlerName, eventsHelper._raiseException):
            events.trigger(failname)
    except Exception:
        # The event should should be unbound at this point
        events.trigger(failname)


@unittest.mock.patch.object(events, 'daemon', new=events.AsyncEventsThread())
def testAsyncEvents(eventsHelper):
    name, failname = '_test.event', '_test.failure'
    handlerName = '_test.handler'

    def callback(event):
        eventsHelper.ctr += 1
        eventsHelper.responses = event.responses

    with events.bound(failname, handlerName, eventsHelper._raiseException), \
            events.bound(name, handlerName, eventsHelper._incrementWithResponse):
        # Make sure an async handler that fails does not break the event
        # loop and that its callback is not triggered.
        assert events.daemon.eventQueue.qsize() == 0
        events.daemon.trigger(failname, handlerName, callback)

        # Triggering the event before the daemon starts should do nothing
        assert events.daemon.eventQueue.qsize() == 1
        events.daemon.trigger(name, {'amount': 2}, callback)
        assert events.daemon.eventQueue.qsize() == 2
        assert eventsHelper.ctr == 0

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
                if eventsHelper.ctr == 3:
                    break
            if time.time() - startTime > 15:
                break
            time.sleep(0.1)
        assert events.daemon.eventQueue.qsize() == 0
        assert eventsHelper.ctr == 3
        assert eventsHelper.responses == ['foo']
        events.daemon.stop()


@unittest.mock.patch.object(events, 'daemon', new=events.ForegroundEventsDaemon())
def testForegroundDaemon(eventsHelper):
    assert isinstance(events.daemon, events.ForegroundEventsDaemon)

    # Should still be able to call start
    events.daemon.start()

    def callback(event):
        eventsHelper.ctr += 1
        eventsHelper.responses = event.responses

    with events.bound('_test.event', '_test.handler', eventsHelper._raiseException):
        with pytest.raises(Exception, match='^Failure condition$'):
            events.daemon.trigger('_test.event', None, callback)

    with events.bound('_test.event', '_test.handler', eventsHelper._incrementWithResponse):
        events.daemon.trigger('_test.event', {'amount': 2}, callback)

    assert eventsHelper.ctr == 3
    assert eventsHelper.responses == ['foo']

    events.daemon.stop()
