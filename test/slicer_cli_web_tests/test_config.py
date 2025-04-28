import pytest
from pytest_girder.assertions import assertStatus, assertStatusOk

from slicer_cli_web.config import PluginSettings


@pytest.mark.plugin('slicer_cli_web')
def test_default_task_folder(server, admin, folder):
    # Test the setting
    resp = server.request('/system/setting', method='PUT', params={
        'key': PluginSettings.SLICER_CLI_WEB_TASK_FOLDER,
        'value': 'bad value'
    }, user=admin)
    assertStatus(resp, 400)
    resp = server.request('/system/setting', method='PUT', params={
        'key': PluginSettings.SLICER_CLI_WEB_TASK_FOLDER,
        'value': folder['_id']
    }, user=admin)
    assertStatusOk(resp)

    assert PluginSettings.has_task_folder()
    assert PluginSettings.get_task_folder()['_id'] == folder['_id']
