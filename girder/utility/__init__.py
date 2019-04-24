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

import cherrypy
import datetime
import dateutil.parser
import errno
import json
import os
import pytz
import re
import string
import six

import girder
import girder.events

try:
    from random import SystemRandom
    random = SystemRandom()
    random.random()  # potentially raises NotImplementedError
except NotImplementedError:
    girder.logprint.warning(
        'WARNING: using non-cryptographically secure PRNG.')
    import random


def parseTimestamp(x, naive=True):
    """
    Parse a datetime string using the python-dateutil package.

    If no timezone information is included, assume UTC. If timezone information
    is included, convert to UTC.

    If naive is True (the default), drop the timezone information such that a
    naive datetime is returned.
    """
    dt = dateutil.parser.parse(x)
    if dt.tzinfo:
        dt = dt.astimezone(pytz.utc).replace(tzinfo=None)
    if naive:
        return dt
    else:
        return pytz.utc.localize(dt)


def genToken(length=64):
    """
    Use this utility function to generate a random string of a desired length.
    """
    return ''.join(random.choice(string.ascii_letters + string.digits)
                   for _ in range(length))


def camelcase(value):
    """
    Convert a module name or string with underscores and periods to camel case.

    :param value: the string to convert
    :type value: str
    :returns: the value converted to camel case.
    """
    return ''.join(x.capitalize() if x else '_' for x in
                   re.split("[._]+", value))


def mkdir(path, mode=0o777, recurse=True, existOk=True):
    """
    Create a new directory or ensure a directory already exists.

    :param path: The directory to create.
    :type path: str
    :param mode: The mode (permission mask) prior to applying umask.
    :type mode: int
    :param recurse: Whether intermediate missing dirs should be created.
    :type recurse: bool
    :param existOk: Set to True to suppress the error if the dir exists.
    :type existOk: bool
    """
    method = os.makedirs if recurse else os.mkdir

    try:
        method(path, mode)
    except OSError as exc:
        if existOk and exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def toBool(val):
    """
    Coerce a string value to a bool. Meant to be used to parse HTTP
    parameters, which are always sent as strings. The following string
    values will be interpreted as True:

      - ``'true'``
      - ``'on'``
      - ``'1'``
      - ``'yes'``

    All other strings will be interpreted as False. If the given param
    is not passed at all, returns the value specified by the default arg.
    This function is case-insensitive.

    :param val: The value to coerce to a bool.
    :type val: str
    """
    if isinstance(val, bool):
        return val

    return val.lower().strip() in ('true', 'on', '1', 'yes')


class JsonEncoder(json.JSONEncoder):
    """
    This extends the standard json.JSONEncoder to allow for more types to be
    sensibly serialized. This is used in Girder's REST layer to serialize
    route return values when JSON is requested.
    """
    def default(self, obj):
        event = girder.events.trigger('rest.json_encode', obj)
        if len(event.responses):
            return event.responses[-1]

        if isinstance(obj, set):
            return tuple(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.replace(tzinfo=pytz.UTC).isoformat()
        return str(obj)


class RequestBodyStream(object):
    """
    Wraps a cherrypy request body into a more abstract file-like object.
    """
    _ITER_CHUNK_LEN = 65536

    def __init__(self, stream, size=None):
        self.stream = stream
        self.size = size

    def read(self, *args, **kwargs):
        return self.stream.read(*args, **kwargs)

    def close(self, *args, **kwargs):
        pass

    def __iter__(self):
        return self

    def __len__(self):
        return self.getSize()

    def next(self):
        data = self.read(self._ITER_CHUNK_LEN)
        if not data:
            raise StopIteration
        return data

    def __next__(self):
        return self.next()

    def getSize(self):
        """
        Returns the size of the body data wrapped by this class. For
        multipart encoding, this is the size of the part. For sending
        as the body, this is the Content-Length header.
        """
        if self.size is not None:
            return self.size

        return int(cherrypy.request.headers['Content-Length'])


def optionalArgumentDecorator(baseDecorator):
    """
    This decorator can be applied to other decorators, allowing the target decorator to be used
    either with or without arguments.

    The target decorator is expected to take at least 1 argument: the function to be wrapped. If
    additional arguments are provided by the final implementer of the target decorator, they will
    be passed to the target decorator as additional arguments.

    For example, this may be used as:

    .. code-block:: python

        @optionalArgumentDecorator
        def myDec(fun, someArg=None):
            ...

        @myDec
        def a(...):
            ...

        @myDec()
        def a(...):
            ...

        @myDec(5)
        def a(...):
            ...

        @myDec(someArg=5)
        def a(...):
            ...

    :param baseDecorator: The target decorator.
    :type baseDecorator: callable
    """
    @six.wraps(baseDecorator)
    def normalizedArgumentDecorator(*args, **kwargs):
        if len(args) == 1 and callable(args[0]):  # Applied as a raw decorator
            decoratedFunction = args[0]
            # baseDecorator must wrap and return decoratedFunction
            return baseDecorator(decoratedFunction)
        else:   # Applied as a argument-containing decorator
            # Decoration will occur in two passes:
            #   * Now, the decorator arguments are passed, and a new decorator should be returned
            #   * Afterwards, the new decorator will be called to decorate the decorated function
            decoratorArgs = args
            decoratorKwargs = kwargs

            def partiallyAppliedDecorator(decoratedFunction):
                return baseDecorator(decoratedFunction, *decoratorArgs, **decoratorKwargs)
            return partiallyAppliedDecorator

    return normalizedArgumentDecorator
