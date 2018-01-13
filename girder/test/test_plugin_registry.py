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

import distutils

import mock
import pytest
import six

from girder import _plugin as plugin


@pytest.fixture
def logprint():
    with mock.patch.object(plugin, 'logprint') as logprintMock:
        yield logprintMock


def mockPluginGenerator(deps, side_effect=None):
    class MockedPlugin(plugin.GirderPlugin):

        def __init__(self, *args, **kwargs):
            self._mockLoad = mock.Mock()
            super(MockedPlugin, self).__init__(*args, **kwargs)

        def load(self, *args, **kwargs):
            for dep in deps:
                plugin.getPlugin(dep).load(dep)

            self._mockLoad(*args, **kwargs)
            if side_effect:
                raise side_effect

    return MockedPlugin


class MockDistribution(object):
    def __init__(self, name, version, description='', url=''):
        self.PKG_INFO = 'PKG_INFO'
        self.version = version
        self._metadata = self.generateMetadata(name, version, description, url)

    def get_metadata(self, *args, **kwargs):
        return self._metadata

    def generateMetadata(self, name, version, description, url):
        meta = distutils.dist.DistributionMetadata()
        meta.name = name
        meta.version = version
        meta.description = description
        meta.url = url
        pkgInfo = six.StringIO()
        meta.write_pkg_file(pkgInfo)
        return pkgInfo.getvalue()


class MockEntryPoint(object):
    def __init__(self, name, version, description, url, pluginClass):
        self.name = name
        self.description = description
        self.url = url
        self.dist = MockDistribution(name, version, description, url)
        self.load = mock.Mock(return_value=pluginClass)
        self.pluginClass = pluginClass


def mockEntryPointGenerator(name, version='0.1.0', deps=None, side_effect=None):
    if deps is None:
        deps = []

    url = 'url for %s' % name
    doc = 'doc for %s' % name
    pluginClass = mockPluginGenerator(deps, side_effect)
    return MockEntryPoint(name, version, doc, url, pluginClass)


@pytest.fixture
def pluginRegistry():
    yield plugin._pluginRegistry
    plugin._pluginRegistry = None
    plugin._pluginFailureInfo = {}
    plugin._pluginLoadOrder = []


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
    mockEntryPointGenerator('withdeps4', deps=['withdeps3']),
    mockEntryPointGenerator('withdeps1', deps=['leaf1']),
    mockEntryPointGenerator('leaf1'),
    mockEntryPointGenerator('leaf2'),
    mockEntryPointGenerator('leaf3'),
    mockEntryPointGenerator('leaf4'),
    mockEntryPointGenerator('withdeps2', deps=['withdeps1', 'leaf1', 'leaf2']),
    mockEntryPointGenerator('withdeps3', deps=['withdeps2', 'withdeps1'])
]
validPluginList = [
    [],
    [mockEntryPointGenerator('nodeps')],
    [
        mockEntryPointGenerator('nodeps1'),
        mockEntryPointGenerator('nodeps2')
    ],
    [
        mockEntryPointGenerator('withdeps', '1.0.0', ['depa', 'depb']),
        mockEntryPointGenerator('depa'),
        mockEntryPointGenerator('depb')
    ],
    [
        mockEntryPointGenerator('withwebdeps'),
        mockEntryPointGenerator('depa'),
        mockEntryPointGenerator('depb')
    ],
    [
        mockEntryPointGenerator('withmultideps', deps=['depa', 'depb']),
        mockEntryPointGenerator('depa'),
        mockEntryPointGenerator('depb'),
        mockEntryPointGenerator('depc')
    ],
    validPluginTree
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


def testPluginWithNoLoadMethod(registerPlugin, logprint):
    class InvalidPlugin(plugin.GirderPlugin):
        pass
    entrypoint = MockEntryPoint('invalid', '1.0.0', 'description', 'url', InvalidPlugin)
    registerPlugin(entrypoint)
    with pytest.raises(NotImplementedError):
        plugin.getPlugin('invalid').load({})
    logprint.exception.assert_called_once_with('Failed to load plugin invalid')


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
        assert pluginDefinition.description == pluginEntryPoint.description
        assert pluginDefinition.url == pluginEntryPoint.url


@pytest.mark.parametrize('pluginList', validPluginList)
def testPluginLoad(registerPlugin, pluginList, logprint):
    registerPlugin(*pluginList)
    for pluginEntryPoint in pluginList:
        pluginDefinition = plugin.getPlugin(pluginEntryPoint.name)
        pluginDefinition.load({})
        assert pluginDefinition.loaded is True
        logprint.info.assert_any_call('Loaded plugin %s' % pluginEntryPoint.name)


def testPluginLoadOrder(registerPlugin, logprint):
    registerPlugin(*validPluginTree)
    plugin.getPlugin('withdeps3').load({})
    assert plugin.loadedPlugins() == ['leaf1', 'withdeps1', 'leaf2', 'withdeps2', 'withdeps3']
    logprint.info.assert_has_calls([
        mock.call('Loaded plugin leaf1'),
        mock.call('Loaded plugin withdeps1'),
        mock.call('Loaded plugin leaf2'),
        mock.call('Loaded plugin withdeps2'),
        mock.call('Loaded plugin withdeps3')
    ])


def testLoadPluginWithError(registerPlugin, logprint):
    registerPlugin(*pluginTreeWithLoadFailure)
    with pytest.raises(Exception) as exception1:
        plugin.getPlugin('loadfailurea').load({})

    logprint.exception.assert_called_once_with('Failed to load plugin loadfailurea')
    assert 'loadfailurea' in plugin.getPluginFailureInfo()

    with pytest.raises(Exception) as exception2:
        plugin.getPlugin('loadfailurea').load({})

    assert exception1.value == exception2.value


def testLoadMultiplePluginsWithFailure(registerPlugin, logprint):
    registerPlugin(*pluginTreeWithLoadFailure)
    plugin.loadPlugins(['loadfailurea', 'leafa'], {})

    logprint.exception.assert_called_once_with('Failed to load plugin loadfailurea')
    assert 'loadfailurea' in plugin.getPluginFailureInfo()
    assert plugin.loadedPlugins() == ['leafa']


def testLoadPluginTreeWithFailure(registerPlugin, logprint):
    registerPlugin(*pluginTreeWithLoadFailure)
    plugin.loadPlugins(['rootdepends'], {})
    assert plugin.loadedPlugins() == ['leafb', 'leafa', 'withdeps']
    logprint.exception.assert_has_calls([
        mock.call('Failed to load plugin loadfailurea'),
        mock.call('Failed to load plugin dependsonfailure'),
        mock.call('Failed to load plugin rootdepends')
    ])
    assert set(plugin.getPluginFailureInfo().keys()) == {'rootdepends', 'loadfailurea',
                                                         'dependsonfailure'}


def testLoadMissingDependency(registerPlugin, logprint):
    registerPlugin(*validPluginTree)
    plugin.loadPlugins(['missing'], {})
    logprint.error.assert_called_once_with('Plugin missing is not installed')
