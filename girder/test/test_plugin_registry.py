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

import re

import mock
import pytest

from girder import _plugin as plugin


@pytest.fixture
def logprint():
    with mock.patch.object(plugin, 'logprint') as logprintMock:
        yield logprintMock


def assertNoDuplicates(loadOrder):
    __tracebackhide__ = True
    assert len(loadOrder) == len(set(loadOrder))


def assertPluginLoadOrder(plugin, loadOrder):
    __tracebackhide__ = True

    assertNoDuplicates(loadOrder)
    pluginIndex = loadOrder.index(plugin.name)
    for dep in plugin.dependencies:
        depIndex = loadOrder.index(dep)
        assert depIndex < pluginIndex


def assertAllPluginsLoadOrder(loadOrder):
    __tracebackhide__ = True

    assertNoDuplicates(loadOrder)
    for pluginName in loadOrder:
        assertPluginLoadOrder(plugin.getPlugin(pluginName), loadOrder)


class MockedPlugin(plugin.GirderPlugin):
    _side_effect = None

    def __init__(self, *args, **kwargs):
        self._mockLoad = mock.Mock()
        super(MockedPlugin, self).__init__(*args, **kwargs)

    def load(self, *args, **kwargs):
        super(MockedPlugin, self).load(*args, **kwargs)
        self._mockLoad(*args, **kwargs)
        if self._side_effect:
            raise self._side_effect


def mockPluginGenerator(deps, webDeps, url, doc, side_effect=None):
    class GeneratedMockPlugin(MockedPlugin):
        DEPENDENCIES = deps
        WEB_DEPENDENCIES = webDeps
        URL = url
        _side_effect = side_effect
        __doc__ = doc

    return GeneratedMockPlugin


class MockEntryPoint(object):
    def __init__(self, name, version, pluginClass):
        self.name = name
        self.dist = mock.Mock()
        self.dist.version = version
        self.load = mock.Mock(return_value=pluginClass)
        self.pluginClass = pluginClass


def mockEntryPointGenerator(name, version='0.1.0', deps=None, webDeps=None, side_effect=None):
    if deps is None:
        deps = []
    if webDeps is None:
        webDeps = []

    url = 'url for %s' % name
    doc = 'doc for %s' % name
    pluginClass = mockPluginGenerator(deps, webDeps, url, doc, side_effect)
    return MockEntryPoint(name, version, pluginClass)


@pytest.fixture
def pluginRegistry():
    yield plugin._pluginRegistry
    plugin._pluginRegistry = None
    plugin._pluginFailureInfo = {}


@pytest.fixture
def registerPlugin(pluginRegistry):
    entry_points = []

    def iter_entry_points(*args, **kwargs):
        for ep in entry_points:
            yield ep

    def register(*args):
        entry_points.extend(args)

    with mock.patch.object(plugin, 'iter_entry_points', side_effect=iter_entry_points):
        yield register


validPluginTree = [
    mockEntryPointGenerator('withdeps4', deps=['withdeps3'], webDeps=['leaf1', 'leaf4']),
    mockEntryPointGenerator('withdeps1', deps=['leaf1']),
    mockEntryPointGenerator('leaf1'),
    mockEntryPointGenerator('leaf2'),
    mockEntryPointGenerator('leaf3'),
    mockEntryPointGenerator('leaf4'),
    mockEntryPointGenerator('withdeps2', deps=['withdeps1', 'leaf1', 'leaf2']),
    mockEntryPointGenerator('withdeps3', deps=['withdeps2', 'withdeps1'], webDeps=['leaf3'])
]
validPluginList = [
    [],
    [mockEntryPointGenerator('nodeps')],
    [
        mockEntryPointGenerator('withdeps', '1.0.0', ['depa', 'depb']),
        mockEntryPointGenerator('depa'),
        mockEntryPointGenerator('depb')
    ],
    [
        mockEntryPointGenerator('withwebdeps', webDeps=['depa', 'depb']),
        mockEntryPointGenerator('depa'),
        mockEntryPointGenerator('depb')
    ],
    [
        mockEntryPointGenerator('withmultideps', deps=['depa', 'depb'], webDeps=['depb', 'depc']),
        mockEntryPointGenerator('depa'),
        mockEntryPointGenerator('depb'),
        mockEntryPointGenerator('depc')
    ],
    validPluginTree
]
pluginTreeWithCycle = [
    mockEntryPointGenerator('plugin1', deps=['plugin2']),
    mockEntryPointGenerator('plugin2', deps=['plugin3']),
    mockEntryPointGenerator('plugin3', deps=['plugin1'])
]
pluginTreeWithLoadFailure = [
    mockEntryPointGenerator('loadfailurea', side_effect=Exception('failure a')),
    mockEntryPointGenerator('loadfailureb', side_effect=Exception('failure b')),
    mockEntryPointGenerator('dependsonfailure', deps=['loadfailurea']),
    mockEntryPointGenerator('leafa'),
    mockEntryPointGenerator('leafb'),
    mockEntryPointGenerator('withdeps', deps=['leafa', 'leafb']),
    mockEntryPointGenerator('multipledepends', deps=['leafa', 'loadfailureb']),
    mockEntryPointGenerator('rootdepends', deps=['leafb', 'withdeps', 'dependsonfailure'])
]


@pytest.mark.parametrize('pluginList', validPluginList)
def testAllPlugins(registerPlugin, pluginList):
    registerPlugin(*pluginList)
    allPlugins = plugin.allPlugins()
    assert len(allPlugins) == len(pluginList)
    for pluginClass in pluginList:
        assert pluginClass.name in allPlugins


@pytest.mark.parametrize('pluginList', validPluginList)
def testPluginGetMetadata(registerPlugin, pluginList):
    registerPlugin(*pluginList)
    for pluginEntryPoint in pluginList:
        pluginDefinition = plugin.getPlugin(pluginEntryPoint.name)
        assert pluginDefinition.name == pluginEntryPoint.name
        assert pluginDefinition.version == pluginEntryPoint.dist.version
        assert pluginDefinition.description == pluginEntryPoint.pluginClass.__doc__
        assert pluginDefinition.url == pluginEntryPoint.pluginClass.URL


@pytest.mark.parametrize('pluginList', validPluginList)
def testPluginLoad(registerPlugin, pluginList):
    registerPlugin(*pluginList)
    for pluginEntryPoint in pluginList:
        pluginDefinition = plugin.loadPlugin(pluginEntryPoint.name, 'root', 'appconf')
        assert pluginDefinition.loaded is True


def testPluginLoadOnlyOnce(registerPlugin):
    registerPlugin(mockEntryPointGenerator('nodeps'))
    pluginDefinition = plugin.getPlugin('nodeps')
    assert pluginDefinition.loaded is False
    pluginDefinition._mockLoad.assert_not_called()

    plugin.loadPlugin('nodeps', 'root', 'appconf')
    assert pluginDefinition.loaded is True
    pluginDefinition._mockLoad.assert_called_once()

    plugin.loadPlugin('nodeps', 'root', 'appconf')
    assert pluginDefinition.loaded is True
    pluginDefinition._mockLoad.assert_called_once()


def testPluginLoadOrder(registerPlugin):
    registerPlugin(*validPluginTree)
    manager = mock.Mock()
    allPlugins = plugin.allPlugins()
    assert len(allPlugins) == len(validPluginTree)

    for pluginName in plugin.allPlugins():
        pluginClass = plugin.getPlugin(pluginName)
        manager.attach_mock(pluginClass._mockLoad, pluginName)
    plugin.loadPlugin('withdeps4', 'root', 'appconf')

    loadOrder = []
    for call in manager.mock_calls:
        loadOrder.append(re.search(r'call\.(.+)\(', str(call)).groups()[0])

    assertAllPluginsLoadOrder(loadOrder)


def testMissingDependencyHandler(registerPlugin, logprint):
    registerPlugin(
        mockEntryPointGenerator('hasmissingdeps', deps=['missing'])
    )
    assert plugin.getPlugin('hasmissingdeps')
    assert plugin.loadPlugin('hasmissingdeps', 'root', 'appconf') is None

    logprint.error.assert_any_call('ERROR: Plugin %s not found', 'missing')
    logprint.error.assert_any_call('ERROR: Dependency failure while processing %s',
                                   'hasmissingdeps')


def testListAllPluginsToposorted(registerPlugin):
    registerPlugin(*validPluginTree)
    plugins = plugin.getToposortedPlugins()
    assertAllPluginsLoadOrder(plugins)


def testListPluginsToposortedFromList(registerPlugin):
    registerPlugin(*validPluginTree)
    plugins = plugin.getToposortedPlugins(['withdeps4', 'withdeps2'])
    assert plugins == ['leaf1', 'leaf2', 'withdeps1', 'withdeps2', 'withdeps3', 'withdeps4']


def testListPluginWebDependenciesFromList(registerPlugin):
    registerPlugin(*validPluginTree)
    plugins = plugin.getToposortedWebDependencies(['withdeps4', 'withdeps2'])
    assert plugins == ['withdeps2', 'leaf1', 'leaf4', 'withdeps4']


def testListAllPluginsToposortedFromRoot(registerPlugin):
    registerPlugin(*validPluginTree)
    plugins = plugin.getToposortedPlugins(['withdeps4'])
    assert 'withdeps4' in plugins
    assertAllPluginsLoadOrder(plugins)


def testLoadPluginList(registerPlugin):
    registerPlugin(*validPluginTree)
    loaded = plugin.loadPlugins(['withdeps1', 'leaf4', 'withdeps2'], 'root', 'appconf')
    assert set(loaded.keys()) == {'withdeps1', 'leaf4', 'withdeps2'}
    assert plugin.getPlugin('leaf1').loaded is True


def testLoadPluginListWithMissingDependency(registerPlugin, logprint):
    registerPlugin(*validPluginTree)
    loaded = plugin.loadPlugins(
        ['withdeps1', 'notaplugin', 'leaf4', 'withdeps2'], 'root', 'appconf')
    assert set(loaded.keys()) == {'withdeps1', 'leaf4', 'withdeps2'}
    logprint.error.assert_any_call('ERROR: Plugin %s not found', 'notaplugin')
    assert plugin.getPlugin('leaf1').loaded is True


def testLoadPluginCyclicDepencencyHandler(registerPlugin, logprint):
    registerPlugin(*pluginTreeWithCycle)
    with pytest.raises(Exception, match='Cyclic dependencies encountered'):
        plugin.getToposortedPlugins()
    logprint.error.assert_any_call('Cyclic dependencies encountered while processing plugins')


def testSuccessfulLoadWithBadPlugin(registerPlugin):
    registerPlugin(*pluginTreeWithLoadFailure)
    plugin.loadPlugin('leafa', 'root', 'appconf')


def testLoadPluginWithException(registerPlugin, logprint):
    registerPlugin(*pluginTreeWithLoadFailure)
    assert plugin.loadPlugin('loadfailurea', 'root', 'appconf') is None
    assert set(plugin.getPluginFailureInfo().keys()) == {'loadfailurea'}
    logprint.exception.assert_called_with(
        'ERROR: Failed to execute load method for %s', 'loadfailurea')


def testLoadPluginTreeWithException(registerPlugin, logprint):
    registerPlugin(*pluginTreeWithLoadFailure)
    assert plugin.loadPlugin('rootdepends', 'root', 'appconf') is None
    assert set(plugin.getPluginFailureInfo().keys()) == {
        'dependsonfailure', 'loadfailurea', 'rootdepends'
    }
    logprint.exception.assert_any_call(
        'ERROR: Failed to execute load method for %s', 'loadfailurea')
    logprint.error.assert_any_call(
        'ERROR: Dependency failure while processing %s', 'dependsonfailure')
    logprint.error.assert_any_call(
        'ERROR: Dependency failure while processing %s', 'rootdepends')
