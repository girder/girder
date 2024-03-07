"""
This module contains the Girder events framework. It maintains a global mapping
of events to listeners, and contains utilities for callers to handle or trigger
events identified by a name.

Listeners should bind to events by calling:

    ``girder.events.bind('event.name', 'my.handler', handlerFunction)``

And events should be fired by calling:

    ``girder.events.trigger('event.name', info)``
"""

import contextlib
import logging

from collections import OrderedDict

logger = logging.getLogger(__name__)


class Event:
    """
    An Event object is created when an event is triggered. It is passed to
    each of the listeners of the event, which have a chance to add information
    to the event, and also optionally stop the event from being further
    propagated to other listeners, and also optionally instruct the caller that
    it should not execute its default behavior.
    """

    # We might have a lot of events, so we use __slots__ to make them smaller
    __slots__ = (
        'info',
        'name',
        'propagate',
        'defaultPrevented',
        'responses',
        'currentHandlerName'
    )

    def __init__(self, name, info):
        self.name = name
        self.info = info
        self.propagate = True
        self.defaultPrevented = False
        self.responses = []
        self.currentHandlerName = None

    def preventDefault(self):
        """
        This can be used to instruct the triggerer of the event that the default
        behavior it would normally perform should not be performed. The
        semantics of this action are specific to the context of the event
        being handled, but a common use of this method is for a plugin to
        provide an alternate behavior that will replace the normal way the
        event is handled by the core system.
        """
        self.defaultPrevented = True
        return self

    def stopPropagation(self):
        """
        Listeners should call this on the event they were passed in order to
        stop any other listeners to the event from being executed.
        """
        self.propagate = False
        return self

    def addResponse(self, response):
        """
        Listeners that wish to return data back to the caller who triggered this
        event should call this to append their own response to the event.

        :param response: The response value, which can be any type.
        """
        self.responses.append(response)
        return self


def bind(eventName, handlerName, handler):
    """
    Bind a listener (handler) to the event identified by eventName. It is
    convention that plugins will use their own name as the handlerName, so that
    the trigger() caller can see which plugin(s) responded to the event.

    :param eventName: The name that identifies the event.
    :type eventName: str
    :param handlerName: The name that identifies the handler calling bind().
    :type handlerName: str
    :param handler: The function that will be called when the event is fired.
                    It must accept a single argument, which is the Event that
                    was created by trigger(). This function should not return
                    a value; any data that it needs to pass back to the
                    triggerer should be passed via the addResponse() method of
                    the Event.
    :type handler: function
    """
    if eventName in _deprecated:
        logger.warning('event "%s" is deprecated; %s', eventName, _deprecated[eventName])

    if eventName not in _mapping:
        _mapping[eventName] = OrderedDict()

    if handlerName in _mapping[eventName]:
        logger.warning('Event binding already exists: %s -> %s', eventName, handlerName)
    _mapping[eventName][handlerName] = handler


def unbind(eventName, handlerName):
    """
    Removes the binding between the event and the given listener.

    :param eventName: The name that identifies the event.
    :type eventName: str
    :param handlerName: The name that identifies the handler calling bind().
    :type handlerName: str
    """
    _mapping.get(eventName, {}).pop(handlerName, None)


def unbindAll():
    """
    Clears the entire event map. All bound listeners will be unbound.

     .. warning:: This will also disable internal event listeners, which are
       necessary for normal Girder functionality. This function should generally
       never be called outside of testing.
    """
    _mapping.clear()


@contextlib.contextmanager
def bound(eventName, handlerName, handler):
    """
    A context manager to temporarily bind an event handler within its scope.

    Parameters are the same as those to :py:func:`girder.events.bind`.
    """
    bind(eventName, handlerName, handler)
    try:
        yield
    finally:
        unbind(eventName, handlerName)


def trigger(eventName, info=None, pre=None):
    """
    Fire an event with the given name. All listeners bound on that name will be
    called until they are exhausted or one of the handlers calls the
    stopPropagation() method on the event.

    :param eventName: The name that identifies the event.
    :type eventName: str
    :param info: The info argument to pass to the handler function. The type of
        this argument is opaque, and can be anything.
    :param pre: A function that will be executed prior to the handler being
        executed. It will receive a dict with a "handler" key, (the function),
        "info" key (the info arg to this function), and "eventName" and
        "handlerName" values.
    :type pre: function or None
    """
    e = Event(eventName, info)
    for name, handler in _mapping.get(eventName, {}).items():
        e.currentHandlerName = name
        if pre is not None:
            pre(info=info, handler=handler, eventName=eventName, handlerName=name)
        handler(e)

        if e.propagate is False:
            break

    return e


_deprecated = {}
_mapping = {}
