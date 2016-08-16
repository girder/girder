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
import traceback
import yaml
import importlib

import pkg_resources
from pkg_resources import iter_entry_points

from girder import logprint
from girder.constants import PACKAGE_DIR, ROOT_DIR, ROOT_PLUGINS_PACKAGE
from girder.models.model_base import ValidationException
from girder.utility import config as _config, mail_utils, mkdir


def loadPlugins(plugins, root, appconf, apiRoot=None, curConfig=None,
                buildDag=True):
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
    :param curConfig: A girder config object to use.
    :type curConfig: dict or None
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
    if curConfig is None:
        curConfig = _config.getConfig()

    if 'plugins' in curConfig and 'plugin_directory' in curConfig['plugins']:
        logprint.warning(
            'Warning: the plugin_directory setting is deprecated. Please use '
            'the `girder-install plugin` command and remove this setting from '
            'your config file.')

    if ROOT_PLUGINS_PACKAGE not in sys.modules:
        module = imp.new_module(ROOT_PLUGINS_PACKAGE)
        girder.plugins = module
        sys.modules[ROOT_PLUGINS_PACKAGE] = module

    logprint.info('Resolving plugin dependencies...')

    if buildDag:
        plugins = getToposortedPlugins(plugins, curConfig, ignoreMissing=True)

    for plugin in plugins:
        try:
            root, appconf, apiRoot = loadPlugin(
                plugin, root, appconf, apiRoot, curConfig=curConfig)
            logprint.success('Loaded plugin "%s"' % plugin)
        except Exception:
            logprint.exception(
                'ERROR: Failed to load plugin "%s":' % plugin)

    return root, appconf, apiRoot


def getToposortedPlugins(plugins, curConfig=None, ignoreMissing=False):
    """
    Given a set of plugins to load, construct the full DAG of required plugins
    to load and yields them in toposorted order.
    """
    curConfig = curConfig or _config.getConfig()
    plugins = set(plugins)

    allPlugins = findAllPlugins(curConfig)
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

    try:
        pluginParentDir = getPluginParentDir(name, curConfig)
    except Exception:
        pluginParentDir = ''

    pluginDir = os.path.join(pluginParentDir, name)
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
            info = {
                'name': name,
                'config': appconf,
                'serverRoot': root,
                'apiRoot': apiRoot,
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
        curConfig = _config.getConfig()

    if 'plugins' in curConfig and 'plugin_directory' in curConfig['plugins']:
        pluginDirs = curConfig['plugins']['plugin_directory'].split(':')
    else:
        pluginDirs = [defaultPluginDir()]

    for pluginDir in pluginDirs:
        try:
            mkdir(pluginDir)
        except OSError:
            logprint.warning(
                'Could not create plugin directory %s.' % pluginDir)

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
        curConfig = _config.getConfig()

    pluginDirs = getPluginDirs(curConfig)

    if 'plugins' in curConfig and \
       'plugin_install_path' in curConfig['plugins']:
        pluginDir = curConfig['plugins']['plugin_install_path']
    elif pluginDirs:
        pluginDir = pluginDirs[0]
    else:
        pluginDir = None

    return pluginDir


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
                    except ValueError as e:
                        logprint.exception(
                            'ERROR: Plugin "%s": plugin.json is not valid '
                            'JSON.' % entry_point.name)
            elif pkg_resources.resource_exists(entry_point.name, configYml):
                with pkg_resources.resource_stream(
                        entry_point.name, configYml) as conf:
                    try:
                        data = yaml.safe_load(conf)
                    except yaml.YAMLError as e:
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


def findAllPlugins(curConfig=None):
    """
    Walks the plugins directories to find all of the plugins. If the plugin has
    a plugin.json file, this reads that file to determine dependencies.
    """
    allPlugins = {}

    findEntryPointPlugins(allPlugins)
    pluginDirs = getPluginDirs(curConfig)
    if not pluginDirs:
        logprint.warning('Plugin directory not found.')
        return allPlugins

    for pluginDir in pluginDirs:
        dirs = [dir for dir in os.listdir(pluginDir) if os.path.isdir(
            os.path.join(pluginDir, dir))]

        for plugin in dirs:
            data = {}
            configJson = os.path.join(pluginDir, plugin, 'plugin.json')
            configYml = os.path.join(pluginDir, plugin, 'plugin.yml')
            if os.path.isfile(configJson):
                with open(configJson) as conf:
                    try:
                        data = json.load(conf)
                    except ValueError as e:
                        logprint.exception(
                            'ERROR: Plugin "%s": plugin.json is not valid '
                            'JSON.' % plugin)
            elif os.path.isfile(configYml):
                with open(configYml) as conf:
                    try:
                        data = yaml.safe_load(conf)
                    except yaml.YAMLError as e:
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
