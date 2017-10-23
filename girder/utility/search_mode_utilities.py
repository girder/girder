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
from functools import partial

from girder.models.assetstore import Assetstore
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.item import Item
from girder.models.user import User

"""This is the search mode registry for register all the search mode
with the allowed types and the handler as a 'method' attribute.
Plugins can modify this set to allow other search mode.
By Default only two modes are allowed :
  - text: to search in plain text
  - prefix: to search with a prefix
Their handlers are directly define in the base model.
"""
_allowedSearchMode = {}


def defaultSearchModeHandler(query, mode, types, user, level, limit, offset):
    method = '%sSearch' % mode
    results = {}

    for modelName in types:
        model = _getModel(modelName)

        if model is not None:
            results[modelName] = [
                model.filter(d, user) for d in getattr(model, method)(
                    query=query, user=user, limit=limit, offset=offset, level=level)
            ]
    return results


def getSearchModeHandler(mode):
    if mode in _allowedSearchMode:
        return _allowedSearchMode[mode]
    return None


def addSearchMode(mode, handler):
    """This function is able to modify an existing search mode."""
    _allowedSearchMode[mode] = handler


def removeSearchMode(mode):
    """Return a boolean to know if the mode was removed from the search mode registry or not."""
    if _allowedSearchMode.pop(mode, None) is not None:
        return True
    return False


def _getModel(name):
    if name == 'assetstore':
        return Assetstore()
    elif name == 'collection':
        return Collection()
    elif name == 'folder':
        return Folder()
    elif name == 'group':
        return Group()
    elif name == 'item':
        return Item()
    elif name == 'user':
        return User()
    else:
        return None


# Add dynamically the default search mode
addSearchMode('text', partial(defaultSearchModeHandler, mode='text'))
addSearchMode('prefix', partial(defaultSearchModeHandler, mode='prefix'))
