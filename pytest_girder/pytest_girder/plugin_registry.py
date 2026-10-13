import importlib.metadata
import unittest.mock
from contextlib import contextmanager
from tempfile import gettempdir


class _MockDistribution:
    """
    A minimal stand-in for an ``importlib.metadata.Distribution``.

    This mimics just enough of the interface used by
    :class:`girder.plugin.GirderPlugin` (``metadata``, ``version`` and
    ``location``) to register a plugin that is not actually installed. It is
    intentionally dependency-free; in particular it does not rely on
    ``distutils``, which is deprecated and removed from the standard library in
    Python 3.12.
    """

    def __init__(self, name, version, description='', url='', location=None):
        self.PKG_INFO = 'PKG_INFO'
        self.version = version
        self.location = location or gettempdir()
        # ``importlib.metadata`` exposes package metadata with header names such
        # as ``Summary`` and ``Home-page``.  Older distutils-based metadata used
        # lowercase attribute names.  Provide both so this behaves like either.
        self._metadata = {
            'name': name,
            'version': version,
            'description': description,
            'url': url,
            'Name': name,
            'Version': version,
            'Summary': description,
            'Home-page': url,
        }

    @property
    def metadata(self):
        return self._metadata

    def get_metadata(self, *args, **kwargs):
        return dict(self._metadata)


class _MockEntryPoint:
    def __init__(self, name, version, description, url, package, pluginClass, location):
        self.name = name
        self.description = description
        self.url = url
        self.dist = _MockDistribution(package, version, description, url, location)
        self.load = unittest.mock.Mock(return_value=pluginClass)
        self.pluginClass = pluginClass


class PluginRegistry:

    def __init__(self, include_installed_plugins=True):
        self._include_installed_plugins = include_installed_plugins
        self._plugins = []

    @classmethod
    def generateEntrypoint(cls, name, class_, **kwargs):
        package = kwargs.get('package', 'girder-' + name)
        description = kwargs.get('description', '')
        url = kwargs.get('url', '')
        version = kwargs.get('version', '0.1.0')
        location = kwargs.get('location')
        return _MockEntryPoint(name, version, description, url, package, class_, location)

    def registerTestPlugin(self, name, class_, **kwargs):
        self.registerEntrypoint(self.generateEntrypoint(name, class_, **kwargs))

    def registerEntrypoint(self, entryPoint):
        self._plugins.append(entryPoint)

    def _listPluginEntryPoints(self, *args, **kwargs):
        if self._include_installed_plugins:
            kwargs = kwargs.copy()
            kwargs['group'] = 'girder.plugin'
            if len(args):
                kwargs['group'] = args[0]
                if len(args) > 1:
                    kwargs['name'] = args[1]
            if hasattr(importlib.metadata.entry_points(), 'select'):
                yield from importlib.metadata.entry_points().select(**kwargs)
            else:
                for epk in importlib.metadata.entry_points():
                    for ep in importlib.metadata.entry_points()[epk]:
                        if (ep.group == kwargs['group']
                                and ep.name == kwargs.get('name', ep.name)):
                            yield ep
        yield from self._plugins

    @contextmanager
    def __call__(self):
        from girder import plugin

        try:
            with unittest.mock.patch.object(
                    plugin, '_listPluginEntryPoints',
                    side_effect=self._listPluginEntryPoints) as mock_:
                yield mock_
        finally:
            plugin._pluginRegistry = None
            plugin._pluginLoadOrder = []
            plugin._pluginStaticContent.clear()
