import pytest

from girder.plugin import getPlugin, GirderPlugin
from pytest_girder.assertions import assertStatusOk


class Plugin1(GirderPlugin):
    def load(self, info):
        pass


class Plugin2(GirderPlugin):
    def load(self, info):
        getPlugin('plugin1').load(info)


class Plugin3(GirderPlugin):
    def load(self, info):
        pass


@pytest.mark.plugin('plugin1', Plugin1, enabled=False)
@pytest.mark.plugin('plugin2', Plugin2, enabled=False)
@pytest.mark.plugin('plugin3', Plugin3)
def testGetEnabledPlugins(server, admin):
    resp = server.request('/system/plugins', user=admin)
    assertStatusOk(resp)
    assert set(resp.json['enabled']) == {'plugin3'}
    assert set(resp.json['loaded']) == {'plugin3'}


@pytest.mark.plugin('plugin1', Plugin1, enabled=False)
@pytest.mark.plugin('plugin2', Plugin2)
@pytest.mark.plugin('plugin3', Plugin3, enabled=False)
def testGetEnabledPluginsWithDependency(server, admin):
    resp = server.request('/system/plugins', user=admin)
    assertStatusOk(resp)
    assert set(resp.json['enabled']) == {'plugin2'}
    assert set(resp.json['loaded']) == {'plugin1', 'plugin2'}
