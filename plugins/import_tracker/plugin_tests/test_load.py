import pytest

from girder.plugin import loadedPlugins


@pytest.mark.plugin('import_tracker')
def test_import(server):
    assert 'import_tracker' in loadedPlugins()
