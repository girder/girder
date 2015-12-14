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
import json
import pytz
import re


def camelcase(value):
    """
    Convert a module name or string with underscores and periods to camel case.
    :param value: the string to convert
    :type value: str
    :returns: the value converted to camel case.
    """
    return ''.join(x.capitalize() if x else '_' for x in
                   re.split("[._]+", value))


class JsonEncoder(json.JSONEncoder):
    """
    This extends the standard json.JSONEncoder to allow for more types to be
    sensibly serialized. This is used in Girder's REST layer to serialize
    route return values when JSON is requested.
    """
    def default(self, obj):
        if isinstance(obj, set):
            return tuple(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.replace(tzinfo=pytz.UTC).isoformat()
        return str(obj)
