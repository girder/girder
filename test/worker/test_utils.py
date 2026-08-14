import sys
from unittest import mock

import pytest
from girder_worker.utils import (TeeStdOutCustomWrite, _job_manager, apply_girder_api_url_override,
                                 resolve_girder_api_url, rewrite_url_api_base)


def test_TeeStdOutCustomWrite(capfd):
    nonlocal_ = {'data': ''}

    def _append_to_data(message, **kwargs):
        nonlocal_['data'] += message

    with TeeStdOutCustomWrite(_append_to_data):
        sys.stdout.write('Test String')
        sys.stdout.flush()

    assert nonlocal_['data'] == 'Test String'

    out, err = capfd.readouterr()
    assert out == 'Test String'


def test_resolve_girder_api_url_returns_passed_url_when_env_unset(monkeypatch):
    monkeypatch.delenv('GIRDER_WORKER_API_URL', raising=False)
    assert resolve_girder_api_url('http://server/api/v1') == 'http://server/api/v1'
    assert resolve_girder_api_url(None) is None
    assert resolve_girder_api_url() is None


def test_resolve_girder_api_url_prefers_env_override(monkeypatch):
    monkeypatch.setenv('GIRDER_WORKER_API_URL', 'http://worker-view/api/v1')
    assert resolve_girder_api_url('http://server/api/v1') == 'http://worker-view/api/v1'
    assert resolve_girder_api_url() == 'http://worker-view/api/v1'


@pytest.mark.parametrize('url,original,new,expected', [
    (
        'http://server/api/v1/job/abc',
        'http://server/api/v1',
        'http://worker/api/v1',
        'http://worker/api/v1/job/abc',
    ),
    (
        'http://server/api/v1/job/abc/',
        'http://server/api/v1/',
        'http://worker/api/v1/',
        'http://worker/api/v1/job/abc/',
    ),
    (
        'http://other/api/v1/job/abc',
        'http://server/api/v1',
        'http://worker/api/v1',
        'http://other/api/v1/job/abc',
    ),
    (
        None,
        'http://server/api/v1',
        'http://worker/api/v1',
        None,
    ),
])
def test_rewrite_url_api_base(url, original, new, expected):
    assert rewrite_url_api_base(url, original, new) == expected


def test_rewrite_url_api_base_warns_when_original_missing(caplog):
    url = 'http://server/api/v1/job/abc'
    with caplog.at_level('WARNING', logger='girder_worker'):
        assert rewrite_url_api_base(url, None, 'http://worker/api/v1') == url

    assert any(
        'Cannot rewrite API URL' in record.getMessage()
        and 'original API base URL is missing' in record.getMessage()
        for record in caplog.records
    )


def test_apply_girder_api_url_override_updates_request_and_job_info_spec(monkeypatch):
    monkeypatch.setenv('GIRDER_WORKER_API_URL', 'http://worker/api/v1')
    request = mock.MagicMock()
    request.girder_api_url = 'http://server/api/v1'
    request.apiUrl = 'http://server/api/v1'
    request.jobInfoSpec = {
        'url': 'http://server/api/v1/job/abc123',
        'method': 'PUT',
        'logPrint': True,
    }

    resolved = apply_girder_api_url_override(request)

    assert resolved == 'http://worker/api/v1'
    assert request.girder_api_url == 'http://worker/api/v1'
    assert request.apiUrl == 'http://worker/api/v1'
    assert request.jobInfoSpec['url'] == 'http://worker/api/v1/job/abc123'


def test_apply_girder_api_url_override_noop_when_env_unset(monkeypatch):
    monkeypatch.delenv('GIRDER_WORKER_API_URL', raising=False)
    request = mock.MagicMock()
    request.girder_api_url = 'http://server/api/v1'
    request.jobInfoSpec = {'url': 'http://server/api/v1/job/abc123'}

    resolved = apply_girder_api_url_override(request)

    assert resolved == 'http://server/api/v1'
    assert request.girder_api_url == 'http://server/api/v1'
    assert request.jobInfoSpec['url'] == 'http://server/api/v1/job/abc123'


def test_job_manager_uses_api_url_override_from_headers(monkeypatch):
    monkeypatch.setenv('GIRDER_WORKER_API_URL', 'http://worker/api/v1')
    headers = {
        'girder_api_url': 'http://server/api/v1',
        'jobInfoSpec': {
            'url': 'http://server/api/v1/job/abc123',
            'method': 'PUT',
            'logPrint': False,
        },
    }

    manager = _job_manager(headers=headers)

    assert manager.url == 'http://worker/api/v1/job/abc123'
