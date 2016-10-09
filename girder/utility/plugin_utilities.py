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

import codecs
import functools
import girder
import imp
import json
import os
import six
import sys
import yaml
import importlib

import pkg_resources
from pkg_resources import iter_entry_points

from girder import logprint
from girder.constants import GIRDER_ROUTE_ID, GIRDER_STATIC_ROUTE_ID, PACKAGE_DIR, ROOT_DIR, \
    ROOT_PLUGINS_PACKAGE, SettingKey
from girder.models.model_base import ValidationException
from girder.utility import mail_utils, model_importer

_pluginWebroots = {}


def loadPlugins(plugins, root, appconf, apiRoot=None, buildDag=True):
    """
    Loads a set of plugins into the application.

    :param plugins: The set of plugins to load, by directory name.
    :type plugins: list
    :param root: The root node of the server tree.
    :type root: object
    :param appconf: The server's cherrypy configuration object.
    :type appconf: dict
    :param apiRoot: The cherrypy api root object.
    :type apiRoot: object or None
    :param buildDag: If the ``plugins`` parameter is already a topo-sorted list
        with all dependencies resolved, set this to False and it will skip
        rebuilding the DAG. Otherwise the dependency resolution and sorting
        will occur within this method.
    :type buildDag: bool
    :returns: A 3-tuple containing the modified root, config, and apiRoot
        objects.
    :rtype tuple:
    """
    # Register a pseudo-package for the root of all plugins. This must be
    # present in the system module list in order to avoid import warnings.
    if ROOT_PLUGINS_PACKAGE not in sys.modules:
        module = imp.new_module(ROOT_PLUGINS_PACKAGE)
        girder.plugins = module
        sys.modules[ROOT_PLUGINS_PACKAGE] = module

    logprint.info('Resolving plugin dependencies...')

    if buildDag:
        plugins = getToposortedPlugins(plugins, ignoreMissing=True)

    for plugin in plugins:
        try:
            root, appconf, apiRoot = loadPlugin(plugin, root, appconf, apiRoot)
            logprint.success('Loaded plugin "%s"' % plugin)
        except Exception:
            logprint.exception('ERROR: Failed to load plugin "%s":' % plugin)

    return root, appconf, apiRoot


def getToposortedPlugins(plugins, ignoreMissing=False):
    """
    Given a set of plugins to load, construct the full DAG of required plugins
    to load and yields them in toposorted order.
    """
    plugins = set(plugins)

    allPlugins = findAllPlugins()
    dag = {}
    visited = set()

    def addDeps(plugin):
        if plugin not in allPlugins:
            message = 'Required plugin %s does not exist.' % plugin
            if ignoreMissing:
                logprint.error(message)
                return
            else:
                raise ValidationException(message)

        deps = allPlugins[plugin]['dependencies']
        dag[plugin] = deps

        for dep in deps:
            if dep in visited:
                return
            visited.add(dep)
            addDeps(dep)

    for plugin in plugins:
        addDeps(plugin)

    for pset in toposort(dag):
        for plugin in pset:
            yield plugin


def loadPlugin(name, root, appconf, apiRoot=None):
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

    pluginDir = os.path.join(getPluginDir(), name)
    isPluginDir = os.path.isdir(os.path.join(pluginDir, 'server'))
    isPluginFile = os.path.isfile(os.path.join(pluginDir, 'server.py'))
    pluginLoadMethod = None

    if not os.path.exists(pluginDir):
        # Try to load the plugin as an entry_point
        for entry_point in iter_entry_points(group='girder.plugin', name=name):
            pluginLoadMethod = entry_point.load()
            module = importlib.import_module(entry_point.module_name)
            pluginDir = os.path.dirname(module.__file__)
            module.PLUGIN_ROOT_DIR = pluginDir
            girder.plugins.__dict__[name] = module
            isPluginDir = True

    if not os.path.exists(pluginDir):
        raise Exception('Plugin directory does not exist: %s' % pluginDir)
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
            # @todo this query is run for every plugin that's loaded
            setting = model_importer.ModelImporter().model('setting')
            routeTable = setting.get(SettingKey.ROUTE_TABLE)

            info = {
                'name': name,
                'config': appconf,
                'serverRoot': root,
                'serverRootPath': routeTable[GIRDER_ROUTE_ID],
                'apiRoot': apiRoot,
                'staticRoot': routeTable[GIRDER_STATIC_ROUTE_ID],
                'pluginRootDir': os.path.abspath(pluginDir)
            }

            if pluginLoadMethod is None:
                fp, pathname, description = imp.find_module(
                    'server', [pluginDir]
                )
                module = imp.load_module(moduleName, fp, pathname, description)
                module.PLUGIN_ROOT_DIR = pluginDir
                girder.plugins.__dict__[name] = module
                pluginLoadMethod = getattr(module, 'load', None)

            if pluginLoadMethod is not None:
                sys.modules[moduleName] = module
                pluginLoadMethod(info)

            root, appconf, apiRoot = (
                info['serverRoot'], info['config'], info['apiRoot'])

        finally:
            if fp:
                fp.close()

        return root, appconf, apiRoot


def getPluginDir():
    """
    Return the path to the directory that plugins are installed.
    """
    # Check if there is a plugins dir next to the girder dir.
    # This is the case when running from the git repository.
    pluginsDir = os.path.join(ROOT_DIR, 'plugins')
    if os.path.isdir(pluginsDir):
        return pluginsDir
    # Otherwise, we assume we are in a pip-installed environment where plugins is a subdir.
    else:
        return os.path.join(PACKAGE_DIR, 'plugins')


def findEntryPointPlugins(allPlugins):
    # look for plugins enabled via setuptools `entry_points`
    for entry_point in iter_entry_points(group='girder.plugin'):
        # set defaults
        allPlugins[entry_point.name] = {
            'name': entry_point.name,
            'description': '',
            'version': '',
            'dependencies': set()
        }
        configJson = os.path.join('girder', 'plugin.json')
        configYml = os.path.join('girder', 'plugin.yml')
        data = {}
        try:
            if pkg_resources.resource_exists(entry_point.name, configJson):
                with pkg_resources.resource_stream(
                        entry_point.name, configJson) as conf:
                    try:
                        data = json.load(codecs.getreader('utf8')(conf))
                    except ValueError:
                        logprint.exception(
                            'ERROR: Plugin "%s": plugin.json is not valid '
                            'JSON.' % entry_point.name)
            elif pkg_resources.resource_exists(entry_point.name, configYml):
                with pkg_resources.resource_stream(
                        entry_point.name, configYml) as conf:
                    try:
                        data = yaml.safe_load(conf)
                    except yaml.YAMLError:
                        logprint.exception(
                            'ERROR: Plugin "%s": plugin.yml is not valid '
                            'YAML.' % entry_point.name)
        except ImportError:
            pass
        if data == {}:
            data = getattr(entry_point.load(), 'config', {})
        allPlugins[entry_point.name].update(data)
        allPlugins[entry_point.name]['dependencies'] = set(
            allPlugins[entry_point.name]['dependencies'])


def findAllPlugins():
    """
    Walks the plugin directory to find all of the plugins. If the plugin has
    a plugin.json/yml file, this reads that file to determine dependencies.
    """
    allPlugins = {}

    findEntryPointPlugins(allPlugins)
    pluginDir = getPluginDir()

    for plugin in os.listdir(pluginDir):
        data = {}
        configJson = os.path.join(pluginDir, plugin, 'plugin.json')
        configYml = os.path.join(pluginDir, plugin, 'plugin.yml')
        if os.path.isfile(configJson):
            with open(configJson) as conf:
                try:
                    data = json.load(conf)
                except ValueError:
                    logprint.exception(
                        'ERROR: Plugin "%s": plugin.json is not valid '
                        'JSON.' % plugin)
        elif os.path.isfile(configYml):
            with open(configYml) as conf:
                try:
                    data = yaml.safe_load(conf)
                except yaml.YAMLError:
                    logprint.exception(
                        'ERROR: Plugin "%s": plugin.yml is not valid '
                        'YAML.' % plugin)

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


def getPluginWebroots():
    global _pluginWebroots
    return _pluginWebroots


def registerPluginWebroot(webroot, name):
    """
    Adds a webroot to the global registry for plugins based on
    the plugin name.
    """
    global _pluginWebroots

    _pluginWebroots[name] = webroot


class config(object):  # noqa: class name
    """
    Wrap a plugin's ``load`` method appending plugin metadata.

    :param name str: The plugin's name
    :param description str: A brief description of the plugin.
    :param version str: A semver compatible version string.
    :param dependencies list: A list of plugins required by this plugin.
    :param python3 bool: Whether this plugin supports python3.
    :returns: A decorator that appends the metadata to the method
    """
    def __init__(self, **kw):
        self.config = kw

    def __call__(self, func):
        @six.wraps(func)
        def wrapped(*arg, **kw):
            return func(*arg, **kw)
        wrapped.config = self.config
        return wrapped
