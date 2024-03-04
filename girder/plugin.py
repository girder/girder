"""
This module defines functions for registering, loading, and querying girder plugins.
"""

from collections import OrderedDict
from dataclasses import dataclass
import distutils.dist
from functools import wraps
import io
import logging
from pathlib import Path
from pkg_resources import iter_entry_points
from typing import List, OrderedDict as OrderedDictType

from girder import __version__
from girder.exceptions import GirderException

logger = logging.getLogger(__name__)


@dataclass
class PluginStaticContent:
    css: List[str]
    js: List[str]


_NAMESPACE = 'girder.plugin'
_pluginRegistry = None
_pluginLoadOrder = []
_pluginStaticContent: OrderedDictType[str, PluginStaticContent] = OrderedDict()


def getPluginStaticContent():
    return _pluginStaticContent


def registerPluginStaticContent(plugin: str, css: List[str], js: List[str], staticDir: Path, tree):
    from girder.utility.server import _errorDefault

    if plugin not in _pluginStaticContent:
        tree.mount(None, f'/plugin_static/{plugin}', {
            '/': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': str(staticDir),
                'request.show_tracebacks': False,
                'response.headers.server': f'Girder {__version__}',
                'error_page.default': _errorDefault
            }
        })
        _pluginStaticContent[plugin] = PluginStaticContent(
            css=[f'/plugin_static/{plugin}/{f.lstrip("/")}' for f in css],
            js=[f'/plugin_static/{plugin}/{f.lstrip("/")}' for f in js],
        )


class _PluginMeta(type):
    """
    This is a metaclass applied to the ``GirderPlugin`` descriptor class.  It
    exists to automatically wrap subclass load methods.
    """

    def __new__(cls, classname, bases, classdict):
        if 'load' in classdict:
            classdict['load'] = _PluginMeta._wrapPluginLoad(classdict['load'])
        return type.__new__(cls, classname, bases, classdict)

    @staticmethod
    def _wrapPluginLoad(func):
        """Wrap a plugin load method to provide logging and ensure it is loaded only once."""
        @wraps(func)
        def wrapper(self, *args, **kwargs):

            if not getattr(self, '_loaded', False):
                # This block is executed on the first call to the function.
                # The return value of the call is saved an attribute on the wrapper
                # for future invocations.
                self._return = func(self, *args, **kwargs)

                self._loaded = True
                _pluginLoadOrder.append(self.name)
                logger.info('Loaded plugin "%s"', self.name)

            return self._return

        return wrapper


class GirderPlugin(metaclass=_PluginMeta):
    """
    This is a base class for describing a girder plugin.  A plugin is registered by adding
    an entrypoint under the namespace ``girder.plugin``.  This entrypoint should return a
    class derived from this class.

    Example ::
        class Cats(GirderPlugin):

            def load(self, info):
                # load dependent plugins
                girder.plugin.getPlugin('pets').load(info)

                import rest  # register new rest endpoints, etc.
    """

    #: This is the named displayed to users on the plugin page.  Unlike the entrypoint name
    #: used internally, this name can be an arbitrary string.
    DISPLAY_NAME = None

    def __init__(self, entrypoint):
        self._name = entrypoint.name
        self._loaded = False
        self._dist = entrypoint.dist
        self._metadata = _readPackageMetadata(self._dist)

    @property
    def name(self):
        """Return the plugin name defaulting to the entrypoint name."""
        return self._name

    @property
    def displayName(self):
        """Return a user-friendly plugin name (defaults to the entrypoint name)."""
        return self.DISPLAY_NAME or self._name

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
    def loaded(self):
        """Return true if this plugin has been loaded."""
        return getattr(self, '_loaded', False)

    def load(self, info):
        raise NotImplementedError('Plugins must define a load method')


def _readPackageMetadata(distribution):
    """Get a metadata object associated with a python package."""
    metadata_string = distribution.get_metadata(distribution.PKG_INFO)
    metadata = distutils.dist.DistributionMetadata()
    metadata.read_pkg_file(io.StringIO(metadata_string))
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
    for entryPoint in iter_entry_points(_NAMESPACE):
        pluginClass = entryPoint.load()
        plugin = pluginClass(entryPoint)
        _pluginRegistry[plugin.name] = plugin
    return _pluginRegistry


def getPlugin(name):
    """Return a plugin configuration object or None if the plugin is not found."""
    registry = _getPluginRegistry()
    return registry.get(name)


def _loadPlugins(info, names=None):
    """Load plugins with the given app info object.

    If `names` is None, all installed plugins will be loaded. If `names` is a
    list, then only those plugins in the provided list will be loaded.
    """
    if names is None:
        names = allPlugins()

    for name in names:
        pluginObject = getPlugin(name)

        if pluginObject is None:
            raise GirderException('Plugin %s is not installed' % name)

        pluginObject.load(info)


def allPlugins():
    """Return a list of all detected plugins."""
    return list(_getPluginRegistry().keys())


def loadedPlugins():
    """Return a list of successfully loaded plugins."""
    return _pluginLoadOrder[:]
