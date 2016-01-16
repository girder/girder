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
import girder
import imp
import json
import os
import six
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
        print(TerminalColor.warning(
            'Warning: the plugin_directory setting is deprecated. Please use '
            'the `girder-install plugin` command and remove this setting from '
            'your config file.'))

    if ROOT_PLUGINS_PACKAGE not in sys.modules:
        module = imp.new_module(ROOT_PLUGINS_PACKAGE)
        girder.plugins = module
        sys.modules[ROOT_PLUGINS_PACKAGE] = module

    print(TerminalColor.info('Resolving plugin dependencies...'))

    filteredDepGraph = {
        pluginName: info['dependencies']
        for pluginName, info in six.viewitems(findAllPlugins(curConfig))
        if pluginName in plugins
    }

    for pset in toposort(filteredDepGraph):
        for plugin in pset:
            try:
                root, appconf, apiRoot = loadPlugin(
                    plugin, root, appconf, apiRoot, curConfig=curConfig)
                print(TerminalColor.success('Loaded plugin "{}"'
                                            .format(plugin)))
            except Exception:
                print(TerminalColor.error(
                    'ERROR: Failed to load plugin "{}":'.format(plugin)))
                traceback.print_exc()

    return root, appconf, apiRoot


def getPluginParentDir(name, curConfig=None):
    """
    Finds the directory a plugin lives in and returns it. This throws
    an exception if it can't find a directory named name in any of the
    set plugin_directory paths.

    :params name: The name of the plugin (i.e. its directory name)
    :type name: str
    """
    for potentialParentDir in getPluginDirs(curConfig):
        if os.path.isdir(os.path.join(potentialParentDir, name)):
            return potentialParentDir

    raise Exception('Plugin directory %s does not exist.' % name)


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

    pluginParentDir = getPluginParentDir(name, curConfig)
    pluginDir = os.path.join(pluginParentDir, name)
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
        mail_utils.addTemplateDirectory(mailTemplatesDir, prepend=True)

    moduleName = '.'.join((ROOT_PLUGINS_PACKAGE, name))

    if moduleName not in sys.modules:
        fp = None
        try:
            fp, pathname, description = imp.find_module('server', [pluginDir])
            module = imp.load_module(moduleName, fp, pathname, description)
            module.PLUGIN_ROOT_DIR = pluginDir
            girder.plugins.__dict__[name] = module

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


def defaultPluginDir():
    """
    Determine what the default plugin directory should be.

    This assumes none have been specified using the plugin_directory
    and/or plugin_install_path option.
    """
    pluginDir = None

    # It looks if there is a plugin directory next
    # to the Girder Python package.  This is the case when running from the
    # git repository.
    if os.path.isdir(os.path.join(ROOT_DIR, 'plugins')):
        pluginDir = os.path.join(ROOT_DIR, 'plugins')
    # As a last resort, use plugins inside the Girder Python package.
    # This is intended to occur when Girder is pip installed.
    else:
        pluginDir = os.path.join(PACKAGE_DIR, 'plugins')

    return pluginDir


def getPluginDirs(curConfig=None):
    """Return an ordered list of directories that plugins can live in."""
    failedPluginDirs = set()

    if curConfig is None:
        curConfig = config.getConfig()

    if 'plugins' in curConfig and 'plugin_directory' in curConfig['plugins']:
        pluginDirs = curConfig['plugins']['plugin_directory'].split(':')
    else:
        pluginDirs = [defaultPluginDir()]

    for pluginDir in pluginDirs:
        if not os.path.exists(pluginDir):
            try:
                os.makedirs(pluginDir)
            except OSError:
                if not os.path.exists(pluginDir):
                    print(TerminalColor.warning(
                        'Could not create plugin directory %s.' % pluginDir))

                    failedPluginDirs.add(pluginDir)

    return [dir for dir in pluginDirs if dir not in failedPluginDirs]


def getPluginDir(curConfig=None):
    """
    Return which directory plugins should be installed in.

    First precedence is the plugin_install_path setting, next is
    the first path specified in plugin_directory. If neither of those
    can be resolved, resort to defaultPluginDir.

    Returns a /path/to the directory plugins should be installed in.
    """
    if curConfig is None:
        curConfig = config.getConfig()

    pluginDirs = getPluginDirs(curConfig)

    if 'plugins' in curConfig and \
       'plugin_install_path' in curConfig['plugins']:
        pluginDir = curConfig['plugins']['plugin_install_path']
    elif pluginDirs:
        pluginDir = pluginDirs[0]
    else:
        pluginDir = None

    return pluginDir

def findPluginConfig(path):
    """
    Given a directory representing a plugin, find its plugin configuration file
    (e.g. girder_plugin.json or plugin.json) and return the full path to that
    file, or ``None`` if no config file was found.

    :param path: The plugin directory.
    :type path: str
    """
    def searchPath():
        yield os.path.join(path, 'girder_plugin.json')
        yield os.path.join(path, 'girder_plugin.yml')
        yield os.path.join(path, 'plugin.json')
        yield os.path.join(path, 'plugin.yml')

    for file in searchPath():
        if os.path.isfile(file):
            return file

    return None


def readPluginConfig(configFile, silent=False):
    """
    Given the path to a plugin's config file, read the information within it
    and return it. Raises a ``ValueError`` if the file could not be parsed
    according to its extension (either .json or .yml). Also raises a ValueError
    if the file does not have a .json or .yml extension.

    :param configFile: The path to the config file.
    :type configFile: str
    :param silent: Whether to suppress printing error messages to stdout.
    :type silent: bool
    """
    with open(configFile) as fd:
        if configFile.endswith('.json'):
            try:
                return json.load(fd)
            except ValueError as e:
                if not silent:
                    print(TerminalColor.error(
                        'ERROR: %s is not valid JSON.' % configFile))
                    print(e)
                raise
        elif configFile.endswith('.yml'):
            try:
                return yaml.safe_load(fd)
            except yaml.YAMLError as e:
                if not silent:
                    print(TerminalColor.error(
                        'ERROR: %s is not valid YAML.' % configFile))
                    print(e)
                six.raise_from(ValueError(e), e)
        else:
            raise ValueError('Unknown config format: %s.' % configFile)


def findAllPlugins(curConfig=None):
    """
    Walks the plugins directories to find all of the plugins. If the plugin has
    a plugin.json file, this reads that file to determine dependencies.
    """
    allPlugins = {}
    pluginDirs = getPluginDirs(curConfig)
    if not pluginDirs:
        print(TerminalColor.warning('Plugin directory not found. No plugins '
              'loaded.'))
        return allPlugins

    for pluginDir in pluginDirs:
        dirs = [dir for dir in os.listdir(pluginDir) if os.path.isdir(
            os.path.join(pluginDir, dir))]

        for plugin in dirs:
            configFile = findPluginConfig(os.path.join(pluginDir, plugin))

            if configFile:
                try:
                    data = readPluginConfig(configFile)
                except ValueError:
                    continue  # Should we skip plugin? Keeping old behavior.
            else:
                data = {}

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
    for k, v in six.viewitems(data):
        v.discard(k)

    # Find all items that don't depend on anything.
    extra = functools.reduce(
        set.union, six.viewvalues(data)) - set(six.viewkeys(data))
    # Add empty dependencies where needed
    data.update({item: set() for item in extra})

    # Perform the topological sort.
    while True:
        ordered = set(item for item, dep in six.viewitems(data) if not dep)
        if not ordered:
            break
        yield ordered
        data = {item: (dep - ordered)
                for item, dep in six.viewitems(data) if item not in ordered}
    # Detect any cycles in the dependency graph.
    if data:
        raise Exception('Cyclic dependencies detected:\n%s' % '\n'.join(
                        repr(x) for x in six.viewitems(data)))


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
