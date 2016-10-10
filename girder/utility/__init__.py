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

import datetime
import dateutil.parser
import errno
import json
import os
import pytz
import re
import string

import girder
import girder.events

try:
    from random import SystemRandom
    random = SystemRandom()
    random.random()  # potentially raises NotImplementedError
except NotImplementedError:  # pragma: no cover
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
