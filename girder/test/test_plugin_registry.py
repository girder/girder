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


def mockPluginGenerator(deps, webDeps, side_effect=None):
    class GeneratedMockPlugin(MockedPlugin):
        _side_effect = side_effect

    return GeneratedMockPlugin


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


def mockEntryPointGenerator(name, version='0.1.0', deps=None, webDeps=None, side_effect=None):
    if deps is None:
        deps = []
    if webDeps is None:
        webDeps = []

    url = 'url for %s' % name
    doc = 'doc for %s' % name
    pluginClass = mockPluginGenerator(deps, webDeps, side_effect)
    return MockEntryPoint(name, version, doc, url, pluginClass)


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
        assert pluginDefinition.description == pluginEntryPoint.description
        assert pluginDefinition.url == pluginEntryPoint.url


@pytest.mark.parametrize('pluginList', validPluginList)
def testPluginLoad(registerPlugin, pluginList):
    registerPlugin(*pluginList)
    for pluginEntryPoint in pluginList:
        pluginDefinition = plugin.getPlugin(pluginEntryPoint.name)
        pluginDefinition.load({})
        assert pluginDefinition.loaded is True
