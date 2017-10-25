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

from girder.models.model_base import ModelImporter, GirderException

"""
This is the search mode registry for register all the search mode
with the allowed types and the handler as a 'method' attribute.
Plugins can modify this set to allow other search mode.
By Default only two modes are allowed :
  - text: to search in plain text
  - prefix: to search with a prefix
Their handlers are directly define in the base model.
"""
_allowedSearchMode = {}


def getSearchModeHandler(mode):
    return _allowedSearchMode.get(mode)


def addSearchMode(mode, handler):
    """
    This function is enable to modify an existing search mode.
    To modify an existing search mode, you must delete it before adding a new handler.
    """
    if _allowedSearchMode.get(mode) is not None:
        raise GirderException('Try to modify an existing search mode.')
    _allowedSearchMode[mode] = handler


def removeSearchMode(mode):
    """Return a boolean to know if the mode was removed from the search mode registry or not."""
    return _allowedSearchMode.pop(mode, None) is not None


def defaultSearchModeHandler(query, mode, types, user, level, limit, offset):
    method = '%sSearch' % mode
    results = {}

    for modelName in types:
        model = ModelImporter().model(modelName)

        if model is not None:
            results[modelName] = [
                model.filter(d, user) for d in getattr(model, method)(
                    query=query, user=user, limit=limit, offset=offset, level=level)
            ]
    return results


# Add dynamically the default search mode
addSearchMode('text', partial(defaultSearchModeHandler, mode='text'))
addSearchMode('prefix', partial(defaultSearchModeHandler, mode='prefix'))
