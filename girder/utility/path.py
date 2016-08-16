#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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

"""This module contains utility methods for parsing girder path strings."""

import re


def encode(token):
    """Escape special characters in a token for path representation.

    :param str token: The token to encode
    :return: The encoded string
    :rtype: str
    """
    return token.replace('\\', '\\\\').replace('/', '\\/')


def decode(token):
    """Unescape special characters in a token from a path representation.

    :param str token: The token to decode
    :return: The decoded string
    :rtype: str
    """
    return token.replace('\/', '/').replace('\\\\', '\\')


def split(path):
    """Split an encoded path string into decoded tokens.

    :param str path: An encoded path string
    :return: A list of decoded tokens
    :rtype: list
    """
    # It would be better to split by the regex `(?<!\\)(?>\\\\)*/`,
    # but python does't support atomic grouping. :(
    chunks = path.split('/')
    processed = [chunks[0]]

    # matches an odd number of backslashes at the end of the string
    escape = re.compile(r'(?<!\\)(?:\\\\)*\\$')

    # Loop through the chunks and check if any of the forward slashes was
    # escaped.
    for chunk in chunks[1:]:
        if escape.search(processed[-1]):
            # join the chunks
            processed[-1] = processed[-1] + '/' + chunk
        else:
            # append a new token
            processed.append(chunk)

    # now decode all of the tokens and return
    return [decode(token) for token in processed]


def join(tokens):
    """Join a list of tokens into an encoded path string.

    :param list tokens: A list of tokens
    :return: The encoded path string
    :rtype: str
    """
    return '/'.join([encode(token) for token in tokens])
