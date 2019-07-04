import os

import pytest


@pytest.fixture
def virtualenv_path(host):
    return os.path.join(
        host.user().home,
        # Molecule playbook vars can't be passed into Testinfra tests, so hardcode the path
        '.virtualenvs/girder'
    )


@pytest.fixture
def config_path(host):
    return os.path.join(
        host.user().home,
        '.girder/girder.cfg'
    )


def test_girder_package(host, virtualenv_path):
    pip_path = os.path.join(virtualenv_path, 'bin/pip')
    packages = host.pip_package.get_packages(pip_path=pip_path)
    assert 'girder' in packages


def test_girder_web_build(host, virtualenv_path):
    web_file_path = os.path.join(virtualenv_path, 'share/girder/static/built/girder_app.min.js')
    assert host.file(web_file_path).is_file


def test_girder_service(host):
    girder_service = host.service('girder')
    assert girder_service.is_enabled
    assert girder_service.is_running


def test_girder_socket_private(host):
    girder_socket = host.socket('tcp://127.0.0.1:8080')
    assert girder_socket.is_listening


def test_girder_socket_public(host):
    girder_socket = host.socket('tcp://0.0.0.0:8080')
    assert not girder_socket.is_listening


def test_girder_config_exists(host, config_path):
    assert host.file(config_path).exists


@pytest.mark.parametrize('option, value', [
    (r'server\.socket_host', r'"127\.0\.0\.1"'),
    (r'tools\.proxy\.on', r'True'),
    (r'uri', r'"mongodb://mongodb:27017/girder"'),
    (r'mode', r'"production"')
])
def test_girder_config_content(host, config_path, option, value):
    config_line_re = r'^%s *= *%s$' % (option, value)
    assert host.file(config_path).contains(config_line_re)
