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
_modelInstances = {'core': {}}


def _camelcase(value):
    """
    Helper method to convert module name to class name.
    """
    return ''.join(str.capitalize(x) if x else '_' for x in value.split("_"))


def _instantiateCoreModel(model):
    global _modelInstances
    className = _camelcase(model)

    try:
        imported = importlib.import_module('girder.models.%s' % model)
    except ImportError:  # pragma: no cover
        raise Exception('Could not load model module "%s"' % model)

    try:
        constructor = getattr(imported, className)
    except AttributeError:  # pragma: no cover
        raise Exception('Incorrect model class name "%s" for model "%s".'
                        % (className, model))

    _modelInstances['core'][model] = constructor()


def _instantiatePluginModel(model, plugin):
    global _modelInstances
    className = _camelcase(model)

    try:
        imported = importlib.import_module(
            'girder.plugins.%s.models.%s' % (plugin, model))
    except ImportError:  # pragma: no cover
        raise Exception('Could not load plugin model "%s" (%s).'
                        % (model, plugin))

    try:
        constructor = getattr(imported, className)
    except AttributeError:  # pragma: no cover
        raise Exception('Incorrect model class name "%s" for model "%s (%s)".'
                        % (className, model, plugin))

    _modelInstances[plugin][model] = constructor()


class ModelImporter(object):
    """
    Any class that wants to have convenient model importing semantics
    should extend/mixin this class.
    """
    def model(self, model):
        """
        Call this to get the instance of the specified core model. It will be
        lazy-instantiated.

        :param model: The name of the model to get. This is the module
                      name, e.g. "folder". The class name must be the
                      upper-camelcased version of that module name, e.g.
                      "Folder".
        :type model: string
        :returns: The instantiated model, which is a singleton.
        """
        global _modelInstances
        if model not in _modelInstances['core']:
            _instantiateCoreModel(model)

        return _modelInstances['core'][model]

    def pluginModel(self, model, plugin):
        """
        Just like model(), but loads the model from the specified plugin.

        :param model: The name of the model to get. This is the module
                      name, e.g. "folder". The class name must be the
                      upper-camelcased version of that module name, e.g.
                      "Folder".
        :type model: string
        :param plugin: The name of the plugin to load the model from
        :type plugin: string
        :returns: The instantiated model, which is a singleton.
        """
        global _modelInstances
        if plugin not in _modelInstances:
            _modelInstances[plugin] = {}

        if model not in _modelInstances[plugin]:
            _instantiatePluginModel(model, plugin)

        return _modelInstances[plugin][model]
