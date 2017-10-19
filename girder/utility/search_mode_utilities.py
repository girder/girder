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


"""This is the search mode registry for register all the search mode
with the allowed types and the handler as a 'method' attribute.
Plugins can modify this set to allow other search mode.
By Default only two modes are allowed :
  - text: to search in plain text
  - prefix: to search with a prefix
Their handlers are directly define in the model base.
"""
_allowedSearchMode = {
    'text': {
        'types': {'collection', 'folder', 'group', 'item', 'user'},
        'method': 'textSearch'
    },
    'prefix': {
        'types': {'collection', 'folder', 'group', 'item', 'user'},
        'method': 'prefixSearch'
    }
}


def getSearchMode():
    return _allowedSearchMode


def addSearchMode(mode, types, handler):
    """This function is able to modify an existing search mode."""
    _allowedSearchMode.update({
        mode: {
            'types': types,
            'method': handler
        }})


def removeSearchMode(mode):
    """Return False if the mode wasn't in the search mode registry."""
    return _allowedSearchMode.pop(mode, False)


def addTypesToExistingSearchMode(mode, types):
    """Input 'types' should be a set of value even if there is only one type."""
    if mode in _allowedSearchMode:
        _allowedSearchMode[mode]['types'] = _allowedSearchMode[mode]['types'].union(types)


def removeTypesToExistingSearchMode(mode, types):
    """Input 'types' should be a set of value even if there is only one type.
    This function remove only the types which are in the allowed type search.
    If more are given they will be ignored.
    """
    if mode in _allowedSearchMode:
        _allowedSearchMode[mode]['types'] = _allowedSearchMode[mode]['types'].difference(types)
