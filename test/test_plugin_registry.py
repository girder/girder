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

import os
import tempfile
try:
    from tempfile import TemporaryDirectory
except ImportError:
    from backports.tempfile import TemporaryDirectory

import mock
import pytest
from pytest_girder.plugin_registry import PluginRegistry

from girder import plugin
from girder.plugin import GirderPlugin


@pytest.fixture
def logprint():
    with mock.patch.object(plugin, 'logprint') as logprintMock:
        yield logprintMock


@pytest.fixture
def registry(request):
    testPluginMarkers = request.node.get_marker('plugin')
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


class NoDeps(GirderPlugin):

    def __init__(self, *args, **kwargs):
        super(NoDeps, self).__init__(*args, **kwargs)
        self._testLoadMock = mock.Mock()

    def load(self, info):
        self._testLoadMock(info)


class PluginWithNPM(NoDeps):
    NPM_PACKAGE_NAME = '@girder/test_plugin'
    NPM_PACKAGE_VERSION = '1.0.0'


class DependsOnPlugin1(NoDeps):
    def load(self, info):
        plugin.getPlugin('plugin1').load(info)
        super(DependsOnPlugin1, self).load(info)


class DependsOnPlugin2(NoDeps):
    def load(self, info):
        plugin.getPlugin('plugin2').load(info)
        super(DependsOnPlugin2, self).load(info)


class DependsOnPlugin1and2(NoDeps):
    def load(self, info):
        plugin.getPlugin('plugin1').load(info)
        plugin.getPlugin('plugin2').load(info)
        super(DependsOnPlugin1and2, self).load(info)


class ThrowsOnLoad(NoDeps):
    def load(self, info):
        super(DependsOnPlugin1and2, self).load(info)
        raise Exception()


@pytest.mark.plugin('invalid', InvalidPlugin)
def testPluginWithNoLoadMethod(registry, logprint):
    with pytest.raises(NotImplementedError):
        plugin.getPlugin('invalid').load({})
    logprint.exception.assert_called_once_with('Failed to load plugin invalid')


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
    pluginDef = plugin.getPlugin('client_plugin')
    assert pluginDef.npmPackages() == {'@girder/test_plugin': '1.0.0'}


@pytest.mark.plugin('client_plugin', PluginWithNPM, location=tempfile.gettempdir())
def testPluginWithDevInstall(registry):
    with TemporaryDirectory() as d:
        pluginDef = plugin.getPlugin('client_plugin')
        pluginDef.CLIENT_SOURCE_PATH = os.path.split(d)[-1]
        assert pluginDef.npmPackages() == {'@girder/test_plugin': 'file:%s' % d}


@pytest.mark.plugin('plugin1', NoDeps)
@pytest.mark.plugin('plugin2', NoDeps)
@pytest.mark.plugin('plugin3', NoDeps)
@pytest.mark.plugin('plugin4', NoDeps)
def testAllPlugins(registry):
    allPlugins = plugin.allPlugins()
    assert sorted(allPlugins) == ['plugin1', 'plugin2', 'plugin3', 'plugin4']


@pytest.mark.plugin('plugin1', NoDeps)
def testSinglePluginLoad(registry, logprint):
    pluginDefinition = plugin.getPlugin('plugin1')
    pluginDefinition.load({})
    assert pluginDefinition.loaded is True
    logprint.success.assert_any_call('Loaded plugin "plugin1"')

    pluginDefinition.load({})
    pluginDefinition._testLoadMock.assert_called_once()


@pytest.mark.plugin('plugin1', NoDeps)
@pytest.mark.plugin('plugin2', DependsOnPlugin1)
@pytest.mark.plugin('plugin3', NoDeps)
def testPluginLoadWithDeps(registry, logprint):
    pluginDefinition = plugin.getPlugin('plugin2')
    pluginDefinition.load({})
    assert pluginDefinition.loaded is True
    logprint.success.assert_any_call('Loaded plugin "plugin2"')

    assert plugin.getPlugin('plugin1').loaded is True
    logprint.success.assert_any_call('Loaded plugin "plugin1"')

    assert plugin.getPlugin('plugin3').loaded is False


@pytest.mark.plugin('plugin0', DependsOnPlugin1and2)
@pytest.mark.plugin('plugin1', NoDeps)
@pytest.mark.plugin('plugin2', DependsOnPlugin1)
@pytest.mark.plugin('plugin3', NoDeps)
def testPluginLoadOrder(registry, logprint):
    plugin.getPlugin('plugin0').load({})
    assert plugin.loadedPlugins() == ['plugin1', 'plugin2', 'plugin0']
    logprint.success.assert_has_calls([
        mock.call('Loaded plugin "plugin1"'),
        mock.call('Loaded plugin "plugin2"'),
        mock.call('Loaded plugin "plugin0"')
    ])


@pytest.mark.plugin('throws', ThrowsOnLoad)
def testLoadPluginWithError(registry, logprint):
    with pytest.raises(Exception) as exception1:
        plugin.getPlugin('throws').load({})

    logprint.exception.assert_called_once_with('Failed to load plugin throws')
    assert 'throws' in plugin.getPluginFailureInfo()

    with pytest.raises(Exception) as exception2:
        plugin.getPlugin('throws').load({})

    assert exception1.value == exception2.value


@pytest.mark.plugin('plugin1', ThrowsOnLoad)
@pytest.mark.plugin('plugin2', NoDeps)
def testLoadMultiplePluginsWithFailure(registry, logprint):
    plugin.loadPlugins(['plugin1', 'plugin2'], {})

    logprint.exception.assert_has_calls([
        mock.call('Failed to load plugin plugin1')
    ])
    assert 'plugin1' in plugin.getPluginFailureInfo()
    assert plugin.loadedPlugins() == ['plugin2']


@pytest.mark.plugin('plugin1', ThrowsOnLoad)
@pytest.mark.plugin('plugin2', DependsOnPlugin1)
@pytest.mark.plugin('plugin3', NoDeps)
def testLoadTreeWithFailure(registry, logprint):
    plugin.loadPlugins(['plugin2', 'plugin3'], {})

    logprint.exception.assert_has_calls([
        mock.call('Failed to load plugin plugin1'),
        mock.call('Failed to load plugin plugin2')
    ])
    assert 'plugin1' in plugin.getPluginFailureInfo()
    assert plugin.loadedPlugins() == ['plugin3']


def testLoadMissingDependency(logprint):
    plugin.loadPlugins(['missing'], {})
    logprint.error.assert_called_once_with('Plugin missing is not installed')


def testRegisterWebroot(registry):
    plugin.registerPluginWebroot('webroot', 'plugin')
    assert plugin.getPluginWebroots() == {'plugin': 'webroot'}
