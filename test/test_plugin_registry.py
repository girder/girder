import tempfile
import unittest.mock

import pytest
from pytest_girder.plugin_registry import PluginRegistry

from girder import plugin
from girder.exceptions import GirderException
from girder.plugin import GirderPlugin


@pytest.fixture
def logprint():
    with unittest.mock.patch.object(plugin, 'logprint') as logprintMock:
        yield logprintMock


@pytest.fixture
def registry(request):
    testPluginMarkers = request.node.iter_markers('plugin')
    pluginRegistry = PluginRegistry(include_installed_plugins=False)
    if testPluginMarkers is not None:
        for testPluginMarker in testPluginMarkers:
            if len(testPluginMarker.args) > 1:
                pluginRegistry.registerTestPlugin(
                    *testPluginMarker.args, **testPluginMarker.kwargs
                )
    with pluginRegistry():
        yield


class InvalidPlugin(GirderPlugin):
    pass


class LoadMockMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._testLoadMock = unittest.mock.Mock()


class NoDeps(LoadMockMixin, GirderPlugin):
    def load(self, info):
        self._testLoadMock(info)


class PluginWithNPM(LoadMockMixin, GirderPlugin):
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        self._testLoadMock(info)


class ReturnsFive(LoadMockMixin, GirderPlugin):
    def load(self, info):
        self._testLoadMock(info)
        return 5


class DependsOnPlugin1(LoadMockMixin, GirderPlugin):
    def load(self, info):
        plugin.getPlugin('plugin1').load(info)
        self._testLoadMock(info)


class DependsOnPlugin2(LoadMockMixin, GirderPlugin):
    def load(self, info):
        plugin.getPlugin('plugin2').load(info)
        self._testLoadMock(info)


class DependsOnPlugin1and2(LoadMockMixin, GirderPlugin):
    def load(self, info):
        plugin.getPlugin('plugin1').load(info)
        plugin.getPlugin('plugin2').load(info)
        self._testLoadMock(info)


class ThrowsOnLoad(LoadMockMixin, GirderPlugin):
    def load(self, info):
        self._testLoadMock(info)
        raise Exception()


class HasDisplayName(LoadMockMixin, GirderPlugin):
    DISPLAY_NAME = 'A plugin with a display name'

    def load(self, info):
        self._testLoadMock(info)


@pytest.mark.plugin('invalid', InvalidPlugin)
def testPluginWithNoLoadMethod(registry):
    with pytest.raises(NotImplementedError):
        plugin.getPlugin('invalid').load({})


@pytest.mark.plugin('display', HasDisplayName)
def testPluginWithDisplayName(registry):
    pluginDef = plugin.getPlugin('display')
    assert pluginDef.name == 'display'
    assert pluginDef.displayName == 'A plugin with a display name'


@pytest.mark.plugin('nodeps', NoDeps)
def testPluginWithNoDisplayName(registry):
    pluginDef = plugin.getPlugin('nodeps')
    assert pluginDef.name == 'nodeps'
    assert pluginDef.displayName == 'nodeps'


@pytest.mark.plugin('nodeps', NoDeps, description='description', version='1.0.0', url='url')
def testPluginMetadata(registry):
    pluginDef = plugin.getPlugin('nodeps')
    assert pluginDef.name == 'nodeps'
    assert pluginDef.version == '1.0.0'
    assert pluginDef.url == 'url'
    assert pluginDef.description == 'description'
    assert pluginDef.npmPackages() == {}


@pytest.mark.plugin('client_plugin', PluginWithNPM)
def testPluginWithNPMPackage(registry):
    with tempfile.NamedTemporaryFile() as packageJson:
        packageJson.write(b'{"name": "@girder/test_plugin"}')
        packageJson.flush()
        pluginDef = plugin.getPlugin('client_plugin')
        with unittest.mock.patch.object(plugin, 'resource_filename', return_value=packageJson.name):
            assert '@girder/test_plugin' in pluginDef.npmPackages()


@pytest.mark.plugin('plugin1', NoDeps)
@pytest.mark.plugin('plugin2', NoDeps)
@pytest.mark.plugin('plugin3', NoDeps)
@pytest.mark.plugin('plugin4', NoDeps)
def testAllPlugins(registry):
    allPlugins = plugin.allPlugins()
    assert set(allPlugins) == {'plugin1', 'plugin2', 'plugin3', 'plugin4'}


@pytest.mark.plugin('plugin1', NoDeps)
def testPluginLoad(registry):
    plugin1Definition = plugin.getPlugin('plugin1')
    assert plugin1Definition is not None
    assert plugin1Definition.loaded is False

    plugin1Definition.load(info={})

    assert plugin1Definition.loaded is True
    plugin1Definition._testLoadMock.assert_called_once()

    # Attempting to load a second time should do nothing
    plugin1Definition._testLoadMock.reset_mock()

    plugin1Definition.load(info={})

    assert plugin1Definition.loaded is True
    plugin1Definition._testLoadMock.assert_not_called()


@pytest.mark.plugin('plugin1', ReturnsFive)
def testPluginLoadReturn(registry):
    plugin1Definition = plugin.getPlugin('plugin1')

    assert plugin1Definition.load(info={}) == 5

    # The value should be returned every time load is called
    assert plugin1Definition.load(info={}) == 5


# plugin._loadPlugins cannot be tested without providing "names", since all built-in Girder plugins
# are typically installed for testing and will be loaded


@pytest.mark.plugin('plugin1', NoDeps)
def testLoadPluginsSingle(registry, logprint):
    plugin._loadPlugins(info={}, names=['plugin1'])

    assert set(plugin.loadedPlugins()) == {'plugin1'}

    plugin1Definition = plugin.getPlugin('plugin1')
    assert plugin1Definition is not None
    assert plugin1Definition.loaded is True
    plugin1Definition._testLoadMock.assert_called_once()

    logprint.success.assert_any_call('Loaded plugin "plugin1"')


@pytest.mark.plugin('throws', ThrowsOnLoad)
def testLoadPluginsWithError(registry):
    with pytest.raises(Exception) as exception1:
        plugin._loadPlugins(info={}, names=['throws'])

    assert plugin.loadedPlugins() == []

    # Try again, as this shouldn't corrupt the loading system
    with pytest.raises(Exception) as exception2:
        plugin._loadPlugins(info={}, names=['throws'])

    # Ensure the exception is new each time
    assert exception1.value is not exception2.value


@pytest.mark.plugin('plugin1', NoDeps)
@pytest.mark.plugin('plugin2', DependsOnPlugin1)
def testLoadPluginsWithDeps(registry, logprint):
    plugin._loadPlugins(info={}, names=['plugin2'])

    assert set(plugin.loadedPlugins()) == {'plugin1', 'plugin2'}

    for pluginName in ['plugin1', 'plugin2']:
        pluginDefinition = plugin.getPlugin(pluginName)
        assert pluginDefinition is not None
        assert pluginDefinition.loaded is True
        pluginDefinition._testLoadMock.assert_called_once()

    # Since plugin1 is the dependant, it must be loaded first
    logprint.success.assert_has_calls([
        unittest.mock.call('Loaded plugin "plugin1"'),
        unittest.mock.call('Loaded plugin "plugin2"')
    ], any_order=False)


@pytest.mark.plugin('plugin1', NoDeps)
@pytest.mark.plugin('plugin2', NoDeps)
@pytest.mark.plugin('plugin3', ThrowsOnLoad)
def testLoadPluginsExclusion(registry):
    # Ignoring installed but not-requested plugins only happens in the testing environment, but
    # is critical functionality
    plugin._loadPlugins(info={}, names=['plugin1'])

    assert set(plugin.loadedPlugins()) == {'plugin1'}

    for pluginName in ['plugin2', 'plugin3']:
        pluginDefinition = plugin.getPlugin(pluginName)
        assert pluginDefinition is not None
        assert pluginDefinition.loaded is False
        pluginDefinition._testLoadMock.assert_not_called()


def testLoadPluginsMissing(registry):
    # This case should not typically happen outside of the testing environment
    with pytest.raises(GirderException, match='Plugin missing is not installed'):
        plugin._loadPlugins(info={}, names=['missing'])

    assert plugin.loadedPlugins() == []


def testRegisterWebroot(registry):
    plugin.registerPluginWebroot('webroot', 'plugin')
    assert plugin.getPluginWebroots() == {'plugin': 'webroot'}
