import distutils
from contextlib import contextmanager
import email.parser
import io
import importlib.metadata
from tempfile import gettempdir
import unittest.mock


class _MockDistribution:
    def __init__(self, name, version, description='', url='', location=None):
        self.PKG_INFO = 'PKG_INFO'
        self.version = version
        self.location = location or gettempdir()
        self._metadata = self._generateMetadata(name, version, description, url)

    @property
    def metadata(self):
        return self._meta.__dict__

    def get_metadata(self, *args, **kwargs):
        return self._metadata

    def _generateMetadata(self, name, version, description, url):
        meta = distutils.dist.DistributionMetadata()
        meta.name = name
        meta.version = version
        meta.description = description
        meta.url = url
        meta.long_description_content_type = None
        meta.project_urls = {}
        meta.provides_extras = ()
        meta.license_file = None
        meta.license_files = None
        meta.license_expression = None
        meta.install_requires = []
        meta.extras_require = {}
        pkgInfo = io.StringIO()
        meta.write_pkg_file(pkgInfo)
        self._meta = meta
        pkgInfo.seek(0)
        return {k: v for k, v in email.parser.Parser().parse(pkgInfo).items()}


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
