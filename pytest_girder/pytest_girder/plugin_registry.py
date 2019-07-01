import distutils
from contextlib import contextmanager
from pkg_resources import iter_entry_points
from tempfile import gettempdir

import mock
import six


class _MockDistribution(object):
    def __init__(self, name, version, description='', url='', location=None):
        self.PKG_INFO = 'PKG_INFO'
        self.version = version
        self.location = location or gettempdir()
        self._metadata = self._generateMetadata(name, version, description, url)

    def get_metadata(self, *args, **kwargs):
        return self._metadata

    def _generateMetadata(self, name, version, description, url):
        meta = distutils.dist.DistributionMetadata()
        meta.name = name
        meta.version = version
        meta.description = description
        meta.url = url
        pkgInfo = six.StringIO()
        meta.write_pkg_file(pkgInfo)
        return pkgInfo.getvalue()


class _MockEntryPoint(object):
    def __init__(self, name, version, description, url, package, pluginClass, location):
        self.name = name
        self.description = description
        self.url = url
        self.dist = _MockDistribution(package, version, description, url, location)
        self.load = mock.Mock(return_value=pluginClass)
        self.pluginClass = pluginClass


class PluginRegistry(object):

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

    def _iter_entry_points(self, *args, **kwargs):
        if self._include_installed_plugins:
            for ep in iter_entry_points(*args, **kwargs):
                yield ep
        for ep in self._plugins:
            yield ep

    @contextmanager
    def __call__(self):
        from girder import plugin

        try:
            with mock.patch.object(
                    plugin, 'iter_entry_points', side_effect=self._iter_entry_points) as mock_:
                yield mock_
        finally:
            plugin._pluginRegistry = None
            plugin._pluginLoadOrder = []
