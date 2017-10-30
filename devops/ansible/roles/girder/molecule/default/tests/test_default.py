import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_girder_pip(host):
    assert 'girder' in host.pip_package.get_packages(pip_path='/root/.virtualenvs/girder/bin/pip')
