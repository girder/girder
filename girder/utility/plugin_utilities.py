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

"""
The purpose of this module is to provide utility functions related to loading
and registering plugins into the system. The "loadPlugins" and "loadPlugin"
functions are used by the core system to actually load the plugins and create
the pseudo-packages required for easily referencing them. The other functions
in this class are general utility functions designed to be used within the
plugins themselves to help them register with the application.
"""

import functools
import imp
import json
import os
import sys
import traceback
import yaml

from girder.constants import PACKAGE_DIR, ROOT_DIR, ROOT_PLUGINS_PACKAGE, \
    TerminalColor
from girder.utility import mail_utils, config


def loadPlugins(plugins, root, appconf, apiRoot=None, curConfig=None):
    """
    Loads a set of plugins into the application. The list passed in should not
    already contain dependency information; dependent plugins will be loaded
    automatically.

    :param plugins: The set of plugins to load, by directory name.
    :type plugins: list
    :param root: The root node of the server tree.
    :param appconf: The server's cherrypy configuration object.
    :type appconf: dict
    :returns: A list of plugins that were actually loaded, once dependencies
              were resolved and topological sort was performed.
    """
    # Register a pseudo-package for the root of all plugins. This must be
    # present in the system module list in order to avoid import warnings.
    if curConfig is None:
        curConfig = config.getConfig()
    if 'plugins' in curConfig and 'plugin_directory' in curConfig['plugins']:
        pluginDir = curConfig['plugins']['plugin_directory']
    elif os.path.exists(os.path.join(PACKAGE_DIR, 'plugins')):
        pluginDir = os.path.join(PACKAGE_DIR, 'plugins')
    else:
        pluginDir = os.path.join(ROOT_DIR, 'plugins')

    if ROOT_PLUGINS_PACKAGE not in sys.modules:
        sys.modules[ROOT_PLUGINS_PACKAGE] = type('', (), {
            '__path__': pluginDir,
            '__package__': ROOT_PLUGINS_PACKAGE,
            '__name__': ROOT_PLUGINS_PACKAGE
        })()

    print TerminalColor.info('Resolving plugin dependencies...')

    filteredDepGraph = {
        pluginName: info['dependencies']
        for pluginName, info in findAllPlugins(curConfig).iteritems()
        if pluginName in plugins
    }

    for pset in toposort(filteredDepGraph):
        for plugin in pset:
            try:
                root, appconf, apiRoot = loadPlugin(
                    plugin, root, appconf, apiRoot, curConfig=curConfig)
                print TerminalColor.success('Loaded plugin "{}"'
                                            .format(plugin))
            except:
                print TerminalColor.error(
                    'ERROR: Failed to load plugin "{}":'.format(plugin))
                traceback.print_exc()

    return root, appconf, apiRoot


def loadPlugin(name, root, appconf, apiRoot=None, curConfig=None):
    """
    Loads a plugin into the application. This means allowing it to create
    endpoints within its own web API namespace, and to register its event
    listeners, and do anything else it might want to do.

    :param name: The name of the plugin (i.e. its directory name)
    :type name: str
    :param root: The root node of the web API.
    :param appconf: The cherrypy configuration for the server.
    :type appconf: dict
    """
    if apiRoot is None:
        apiRoot = root.api.v1

    pluginDir = os.path.join(getPluginDir(curConfig), name)
    isPluginDir = os.path.isdir(os.path.join(pluginDir, 'server'))
    isPluginFile = os.path.isfile(os.path.join(pluginDir, 'server.py'))
    if not os.path.exists(pluginDir):
        raise Exception('Plugin directory does not exist: {}'.format(pluginDir))
    if not isPluginDir and not isPluginFile:
        # This plugin does not have any server-side python code.
        return root, appconf, apiRoot

    mailTemplatesDir = os.path.join(pluginDir, 'server', 'mail_templates')
    if os.path.isdir(mailTemplatesDir):
        # If the plugin has mail templates, add them to the lookup path
        mail_utils.addTemplateDirectory(mailTemplatesDir)

    moduleName = '.'.join((ROOT_PLUGINS_PACKAGE, name))

    if moduleName not in sys.modules:
        fp = None
        try:
            fp, pathname, description = imp.find_module('server', [pluginDir])
            module = imp.load_module(moduleName, fp, pathname, description)
            setattr(module, 'PLUGIN_ROOT_DIR', pluginDir)

            if hasattr(module, 'load'):
                info = {
                    'name': name,
                    'config': appconf,
                    'serverRoot': root,
                    'apiRoot': apiRoot,
                    'pluginRootDir': os.path.abspath(pluginDir)
                }
                module.load(info)

                root, appconf, apiRoot = (
                    info['serverRoot'], info['config'], info['apiRoot'])
        finally:
            if fp:
                fp.close()

        return root, appconf, apiRoot


def getPluginDir(curConfig=None):
    """
    Returns the /path/to the currently configured plugin directory.
    """
    if curConfig is None:
        curConfig = config.getConfig()

    # This uses the plugin directory specified in the config first.
    if 'plugins' in curConfig and 'plugin_directory' in curConfig['plugins']:
        pluginsDir = curConfig['plugins']['plugin_directory']

    # If none is specified, it looks if there is a plugin directory next
    # to the girder python package.  This is the case when running from the
    # git repository.
    elif os.path.isdir(os.path.join(ROOT_DIR, 'plugins')):
        pluginsDir = os.path.join(ROOT_DIR, 'plugins')

    # As a last resort, use plugins inside the girder python package.
    # This is intended to occur when girder is pip installed.
    else:
        pluginsDir = os.path.join(PACKAGE_DIR, 'plugins')
    if not os.path.exists(pluginsDir):
        try:
            os.makedirs(pluginsDir)
        except OSError:
            if not os.path.exists(pluginsDir):
                print(TerminalColor.warning(
                    'Could not create plugin directory.'))
                pluginsDir = None
    return pluginsDir


def findAllPlugins(curConfig=None):
    """
    Walks the plugins directory to find all of the plugins. If the plugin has
    a plugin.json file, this reads that file to determine dependencies.
    """
    allPlugins = {}
    pluginsDir = getPluginDir(curConfig)
    if not pluginsDir:
        print(TerminalColor.warning('Plugin directory not found. No plugins '
              'loaded.'))
        return allPlugins
    dirs = [dir for dir in os.listdir(pluginsDir) if os.path.isdir(
            os.path.join(pluginsDir, dir))]

    for plugin in dirs:
        data = {}
        configJson = os.path.join(pluginsDir, plugin, 'plugin.json')
        configYml = os.path.join(pluginsDir, plugin, 'plugin.yml')
        if os.path.isfile(configJson):
            with open(configJson) as conf:
                try:
                    data = json.load(conf)
                except ValueError as e:
                    print(TerminalColor.error(
                        'ERROR: Failed to load plugin "%s": plugin.json is not '
                        'valid JSON.' % plugin))
                    print e
                    continue
        elif os.path.isfile(configYml):
            with open(configYml) as conf:
                try:
                    data = yaml.safe_load(conf)
                except yaml.YAMLError as e:
                    print(TerminalColor.error(
                        'ERROR: Failed to load plugin "%s": plugin.yml is not '
                        'valid YAML.' % plugin))
                    print e
                    continue

        allPlugins[plugin] = {
            'name': data.get('name', plugin),
            'description': data.get('description', ''),
            'version': data.get('version', ''),
            'dependencies': set(data.get('dependencies', []))
        }

    return allPlugins


def toposort(data):
    """
    General-purpose topological sort function. Dependencies are expressed as a
    dictionary whose keys are items and whose values are a set of dependent
    items. Output is a list of sets in topological order. This is a generator
    function that returns a sequence of sets in topological order.

    :param data: The dependency information.
    :type data: dict
    :returns: Yields a list of sorted sets representing the sorted order.
    """
    if not data:
        return

    # Ignore self dependencies.
    for k, v in data.items():
        v.discard(k)

    # Find all items that don't depend on anything.
    extra = functools.reduce(
        set.union, data.itervalues()) - set(data.iterkeys())
    # Add empty dependencies where needed
    data.update({item: set() for item in extra})

    # Perform the topological sort.
    while True:
        ordered = set(item for item, dep in data.iteritems() if not dep)
        if not ordered:
            break
        yield ordered
        data = {item: (dep - ordered)
                for item, dep in data.iteritems() if item not in ordered}
    # Detect any cycles in the dependency graph.
    if data:
        raise Exception('Cyclic dependencies detected:\n%s' % '\n'.join(
                        repr(x) for x in data.iteritems()))


def addChildNode(node, name, obj=None):
    """
    Use this to build paths to your plugin's endpoints.

    :param node: The parent node to add the child node to.
    :param name: The name of the child node in the URL path.
    :type name: str
    :param obj: The object to place at this new node, or None if this child
                should not be exposed as an endpoint, instead just used as
                an intermediary hidden node.
    :type obj: object or None
    :returns: The node that was created.
    """
    if obj:
        setattr(node, name, obj)
        return obj
    else:
        hiddenNode = type('', (), dict(exposed=False))()
        setattr(node, name, hiddenNode)
        return hiddenNode
