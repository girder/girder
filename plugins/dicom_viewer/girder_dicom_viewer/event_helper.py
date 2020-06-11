# -*- coding: utf-8 -*-
import threading

from girder import events


class _EventHelper:
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
