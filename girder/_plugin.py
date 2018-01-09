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
This module defines functions for registering, loading, and querying girder plugins.
"""

import abc
import distutils
from pkg_resources import iter_entry_points
import traceback

import six

from girder import logprint


NAMESPACE = 'girder.plugin'
_pluginRegistry = None
_pluginFailureInfo = {}


@six.add_metaclass(abc.ABCMeta)
class GirderPlugin(object):
    """
    This is a base class for describing a girder plugin.  A plugin is registered by adding
    an entrypoint under the namespace ``girder.plugin``.  This entrypoint should return a
    class derived from this class.

    Example ::
        class Cats(GirderPlugin):

            def load(self, info):
                super(Cats, self).load()
                import rest  # register new rest endpoints
    """
    DEPENDENCIES = []
    WEB_DEPENDENCIES = []

    def __init__(self, entrypoint):
        self._loaded = False
        self._metadata = _readPackageMetadata(entrypoint.dist)

    @property
    def name(self):
        """Return the plugin name defaulting to the entrypoint name."""
        return self._metadata.name

    @property
    def description(self):
        """Return the plugin description defaulting to the classes docstring."""
        return self._metadata.description

    @property
    def url(self):
        """Return a url reference to the plugin (usually a readthedocs page)."""
        return self._metadata.url

    @property
    def version(self):
        """Return the version of the plugin automatically determined from setup.py."""
        return self._metadata.version

    @property
    def dependencies(self):
        """Return a list of plugins that this plugin requires."""
        return list(self.DEPENDENCIES)

    @property
    def webDependencies(self):
        """Return a list of plugins containing web client assets this plugin uses."""
        return list(self.WEB_DEPENDENCIES)

    @property
    def loaded(self):
        """Return true if this plugin has been loaded."""
        return self._loaded

    @abc.abstractmethod
    def load(self, info):
        """Execute any code necessary to load the plugin.

        This method must be overridden by derived classes and call the superclass method.
        """
        self._loaded = True


def _readPackageMetadata(distribution):
    """Get a metadata object associated with a python package."""
    metadata_string = distribution.get_metadata(distribution.PKG_INFO)
    metadata = distutils.dist.DistributionMetadata()
    metadata.read_pkg_file(six.StringIO(metadata_string))
    return metadata


def _getPluginRegistry():
    """Return a dictionary containing all detected plugins.

    This function will discover plugins registered via entrypoints and return
    a mapping of plugin name -> plugin definition.  The result is memoized
    because iteration through entrypoints is a slow operation.
    """
    global _pluginRegistry
    if _pluginRegistry is not None:
        return _pluginRegistry

    _pluginRegistry = {}
    for entryPoint in iter_entry_points(NAMESPACE):
        pluginClass = entryPoint.load()
        plugin = pluginClass(entryPoint)
        _pluginRegistry[plugin.name] = plugin
    return _pluginRegistry


def _walkPluginTree(func, plugins, dependencyGetter, handled, nodes):
    """Walk through the plugin dependency tree depth first.

    This is a recursive function performing a specialized topological sorting of the
    plugin dependency tree.  Each time a new plugin is encountered the provided function
    is called on the plugin config object.  This function will be called at most once
    for each plugin and if it raises any exception, an error message will be recorded and
    the walk cancelled.

    :param func: A function taking the plugin configuration object.
    :param plugins: A list of plugin names to traverse.
    :param dependencyGetter: A function that returns a list of dependencies of a plugin.
    :param handled: A set of plugin names that have already been handled.
    :param nodes: A set of plugin names in the current tree traversal.  This is used
                  to detect cycles in the dependency graph.
    """
    # loop over a sorted list of plugins to ensure a consistent traversal order
    for pluginName in sorted(plugins):
        if pluginName in handled:
            continue

        # handle dependency cycles
        if pluginName in nodes:
            logprint.error('Cyclic dependencies encountered while processing plugins')
            raise Exception('Cyclic dependencies encountered while processing plugins')

        # generate a set of nodes traversed up to the root for cycle detection
        pluginNodes = {pluginName}
        pluginNodes.update(nodes)

        plugin = getPlugin(pluginName)

        # handle missing dependencies
        if plugin is None:
            logprint.error('ERROR: Plugin %s not found', pluginName)
            raise Exception('Required plugin missing')

        # traverse into sub-dependencies
        try:
            _walkPluginTree(func, dependencyGetter(plugin), dependencyGetter, handled, pluginNodes)
        except Exception:
            logprint.error('ERROR: Dependency failure while processing %s', pluginName)
            _pluginFailureInfo[pluginName] = {
                'traceback': '',
                'message': 'Dependency error'
            }
            handled.add(pluginName)
            raise

        # call the handler function and record it
        func(plugin)
        handled.add(pluginName)


def _getToposortedPlugins(plugins, dependencyGetter):
    """Return a toposorted list of plugins with a custom child-node accessor.

    :param plugins: A list of plugins to include (defaults to all plugins)
    :param dependencyGetter: A function taking a plugin object and returning a list of dependencies
    """
    pluginNames = []
    if plugins is None:
        plugins = allPlugins()

    def appendPluginName(plugin):
        pluginNames.append(plugin.name)

    _walkPluginTree(appendPluginName, plugins, dependencyGetter, set(), set())
    return pluginNames


def getToposortedPlugins(plugins=None):
    """Return a toposorted list of plugins.

    By default this function will return a toposorted list of all detected plugins.  If a list of
    plugin names is provided, it will only return a minimal list of plugins required for the
    given top-level plugins.
    """
    return _getToposortedPlugins(plugins, lambda p: p.dependencies)


def getToposortedWebDependencies(plugins=None):
    """Return a toposorted list of plugin web dependencies.

    By default this function will return a toposorted list of all detected plugins.  If a list of
    plugin names is provided, it will only return a minimal list of plugins required for the
    given top-level plugins.
    """
    return _getToposortedPlugins(
        plugins,
        dependencyGetter=lambda p: p.webDependencies
    )


def getPlugin(name):
    """Return a plugin configuration object or None if the plugin is not found."""
    registry = _getPluginRegistry()
    return registry.get(name)


def getPluginFailureInfo():
    """Return an object containing plugin failure information."""
    return _pluginFailureInfo


def loadPlugin(name, root, appconf, apiRoot=None):
    """Load a plugin and all of its dependencies in topological order."""
    def callPluginLoad(plugin):
        if not plugin or plugin.loaded:
            return
        info['dependencies'] = list(plugin.dependencies)
        try:
            plugin.load(info)
        except Exception:
            logprint.exception('ERROR: Failed to execute load method for %s', plugin.name)
            _pluginFailureInfo[plugin.name] = {
                'traceback': traceback.format_exc()
            }
            raise

    info = {
        'config': appconf,
        'serverRoot': root,
        'apiRoot': apiRoot
    }
    try:
        _walkPluginTree(callPluginLoad, [name], lambda p: p.dependencies, set(), set())
    except Exception:
        return None
    return getPlugin(name)


def loadPlugins(names, root, appconf, apiRoot=None):
    """Load a list of plugins and their dependencies in topological order."""
    loadedPlugins = {}
    for name in names:
        pluginObject = loadPlugin(name, root, appconf, apiRoot)
        if pluginObject:
            loadedPlugins[name] = pluginObject
    return loadedPlugins


def allPlugins():
    """Return a list of all detected plugins."""
    return _getPluginRegistry().keys()
