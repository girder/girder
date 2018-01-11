import pytest
import types


@pytest.mark.testPlugins(['test_plugin'])
def testPluginImportSemantics(server):
    from girder.plugins import test_plugin
    assert isinstance(test_plugin, types.ModuleType) is True
