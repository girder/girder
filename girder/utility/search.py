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

from girder.exceptions import GirderException
from girder.utility.model_importer import ModelImporter

_allowedSearchMode = {}


def getSearchModeHandler(mode):
    """
    Get the handler function for a search mode

    :param mode: A search mode identifier.
    :type mode: str
    :returns: A search mode handler function, or None.
    :rtype: function or None
    """
    return _allowedSearchMode.get(mode)


def addSearchMode(mode, handler):
    """
    Register a search mode.

    New searches made for the registered mode will call the handler function. The handler function
    must take parameters: `query`, `types`, `user`, `level`, `limit`, `offset`, and return the
    search results.

    :param mode: A search mode identifier.
    :type mode: str
    :param handler: A search mode handler function.
    :type handler: function
    """
    if _allowedSearchMode.get(mode) is not None:
        raise GirderException('A search mode %r already exists.' % mode)
    _allowedSearchMode[mode] = handler


def removeSearchMode(mode):
    """
    Remove a search mode.

    This will fail gracefully (returning `False`) if no search mode `mode` was registered.

    :param mode: A search mode identifier.
    :type mode: str
    :returns: Whether the search mode was actually removed.
    :rtype: bool
    """
    return _allowedSearchMode.pop(mode, None) is not None


def _commonSearchModeHandler(mode, query, types, user, level, limit, offset):
    """
    The common handler for `text` and `prefix` search modes.
    """
    # Avoid circular import
    from girder.api.v1.resource import allowedSearchTypes

    method = '%sSearch' % mode
    results = {}

    for modelName in types:
        if modelName not in allowedSearchTypes:
            continue

        if '.' in modelName:
            name, plugin = modelName.rsplit('.', 1)
            model = ModelImporter.model(name, plugin)
        else:
            model = ModelImporter.model(modelName)

        if model is not None:
            results[modelName] = [
                model.filter(d, user) for d in getattr(model, method)(
                    query=query, user=user, limit=limit, offset=offset, level=level)
            ]
    return results


# Add dynamically the default search mode
addSearchMode('text', partial(_commonSearchModeHandler, mode='text'))
addSearchMode('prefix', partial(_commonSearchModeHandler, mode='prefix'))
