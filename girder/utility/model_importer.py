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

import importlib

# We want the models to essentially be singletons, so we keep this centralized
# cache of instantiated models that have been lazy-loaded.
_modelInstances = {}


def _camelcase(value):
    """
    Helper method to convert module name to class name.
    """
    return ''.join(str.capitalize(x) if x else '_' for x in value.split('_'))


def _loadModel(model, module, plugin):
    global _modelInstances
    className = _camelcase(model)

    try:
        imported = importlib.import_module(module)
    except ImportError:  # pragma: no cover
        raise Exception('Could not load model "{}".'.format(module))

    try:
        constructor = getattr(imported, className)
    except AttributeError:  # pragma: no cover
        raise Exception('Incorrect model class name "{}" for model "{}".'
                        .format(className, module))

    _modelInstances[plugin][model] = constructor()


def clearModels():
    """
    Force reloading of all models by clearing the singleton cache. This is
    used by the test suite to ensure that indices are built properly
    at startup.
    """
    global _modelInstances
    _modelInstances = {}


class ModelImporter(object):
    """
    Any class that wants to have convenient model importing semantics
    should extend/mixin this class.
    """
    def model(self, model, plugin='_core'):
        """
        Call this to get the instance of the specified model. It will be
        lazy-instantiated.

        :param model: The name of the model to get. This is the module
                      name, e.g. "folder". The class name must be the
                      upper-camelcased version of that module name, e.g.
                      "Folder".
        :type model: string
        :param plugin: If the model you wish to load is a model within a plugin,
                       set this to the name of the plugin containing the model.
        :returns: The instantiated model, which is a singleton.
        """
        global _modelInstances
        if plugin not in _modelInstances:
            _modelInstances[plugin] = {}

        if model not in _modelInstances[plugin]:
            if plugin == '_core':
                module = 'girder.models.{}'.format(model)
            else:
                module = 'girder.plugins.{}.models.{}'.format(plugin, model)

            _loadModel(model, module, plugin)

        return _modelInstances[plugin][model]
