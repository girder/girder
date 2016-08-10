#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
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
#############################################################################

import cherrypy
import logging
import re


LoggingFilters = []


class regexLoggingFilter(logging.Filter):
    """
    Check log messages against a list of compiled regular expressions.  If any
    of them match, throttle logs.
    """
    def filter(self, record):
        msg = record.getMessage()
        for filter in LoggingFilters:
            if filter['re'].search(msg):
                filter['count'] += 1
                if (filter['frequency'] and
                        filter['count'] >= filter['frequency']):
                    record.msg += ' (%d similar messages)' % filter['count']
                    filter['count'] = 0
                    return True
                return False
        return True


def addLoggingFilter(regex, frequency=None):
    """
    Add a regular expression to the logging filter.  If the regular expression
    matches a registered regex exactly, just update the frequency value.

    :param regex: a regular expression to match against log messages.  For
        matching cherrypy endpoint logging, this should probably be something
        like 'GET /api/v1/item/[0-9a-fA-F]+/download[/ ?#]'.   More generally,
        a value like GET (/[^/ ?#]+)*/item/[^/ ?#]+/download[/ ?#] would be
        agnostic to the api_root.
    :param frequency: either None to never log matching log messages, or an
        integer, where one log message is emitted out of the specified number.
    """
    newFilter = None
    for filter in LoggingFilters:
        if filter['regex'] == regex:
            newFilter = filter
    if not newFilter:
        newFilter = {
            'regex': regex,
            're': re.compile(regex),
            'count': 0
        }
        LoggingFilters.append(newFilter)
    newFilter['frequency'] = frequency


def removeLoggingFilter(regex):
    """
    Remove a regular expression from the logging filter.

    :param regex: the regular expression to remove.
    :returns: True if a filter was removed.
    """
    for idx in range(len(LoggingFilters)):
        if LoggingFilters[idx]['regex'] == regex:
            LoggingFilters[idx:idx + 1] = []
            return True
    return False


for handler in cherrypy.log.access_log.handlers:
    handler.addFilter(regexLoggingFilter())
