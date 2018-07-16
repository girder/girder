import os
import pytest

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


@pytest.mark.parametrize('name', [
    'girder',
    'mongod'
])
def test_services_running_and_enabled(host, name):
    assert host.service(name).is_running
    assert host.service(name).is_enabled


@pytest.mark.parametrize('port', [
    '0.0.0.0:8080',
    '127.0.0.1:27017'
], ids=[
    'girder',
    'mongod'
])
def test_services_listening(host, port):
    assert host.socket('tcp://%s' % port).is_listening
