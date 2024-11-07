from unittest import mock

from docker.api.client import APIClient

from girder_worker.docker.nvidia import is_nvidia_image


def test_is_nvidia_image_no_labels_returns_false():
    api = mock.MagicMock(spec=APIClient)
    api.inspect_image.return_value = {}
    assert is_nvidia_image(api, 'bogus/image:latest') is False


def test_is_nvidia_image_no_nvidia_labels_returns_false():
    api = mock.MagicMock(spec=APIClient)
    api.inspect_image.return_value = {'Config': {'Labels': {'some': 'label'}}}
    assert is_nvidia_image(api, 'bogus/image:latest') is False


def test_is_nvidia_image_returns_true():
    api = mock.MagicMock(spec=APIClient)
    api.inspect_image.return_value = {'Config':
                                      {'Labels':
                                       {'com.nvidia.volumes.needed': 'nvidia_driver'}}}
    assert is_nvidia_image(api, 'bogus/image:latest') is True
