import contextlib
import pytest
from girder import config
from girder.api import access
from pytest_girder.assertions import assertStatus


@contextlib.contextmanager
def serverMode(mode):
    old, config.getConfig()['server']['mode'] = config.getConfig()['server']['mode'], mode
    try:
        yield mode
    finally:
        config.getConfig()['server']['mode'] = old


@pytest.fixture
def exceptionServer(server):
    @access.public
    def _raiseException(*args, **kwargs):
        raise Exception('Specific message')

    server.root.api.v1.item.route('GET', ('exception',), _raiseException)
    yield server
    server.root.api.v1.item.removeRoute('GET', ('exception',))


@pytest.mark.parametrize('mode,msg,hasTrace', [
    ('production', 'An unexpected error occurred on the server.', False),
    ('development', 'Exception: Exception(\'Specific message\',)', True)
])
def testExceptionHandlingBasedOnServerMode(exceptionServer, mode, msg, hasTrace):
    with serverMode(mode):
        resp = exceptionServer.request('/item/exception', exception=True)
        assertStatus(resp, 500)
        assert resp.json['message'] == msg
        assert ('trace' in resp.json) is hasTrace
