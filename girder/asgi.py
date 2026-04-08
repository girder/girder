import asyncio
import logging
import socket
import sys
import threading
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.routing import Mount, WebSocketRoute

from girder.notification import UserNotificationsSocket
from girder.wsgi import app as wsgi_app


class _WSGIBridge:
    """
    Streaming WSGI bridge for ASGI.

    Streams request bodies directly to the WSGI app via a socketpair,
    eliminating async/sync round-trip overhead and large memory copies.
    """

    def __init__(self, wsgi_app):
        self._app = wsgi_app

    def _build_environ(self, scope, body_file):
        environ = {
            'REQUEST_METHOD': scope['method'],
            'SCRIPT_NAME': scope.get('root_path', ''),
            'PATH_INFO': scope.get('path', ''),
            'QUERY_STRING': scope.get('query_string', b'').decode('latin-1'),
            'SERVER_PROTOCOL': f"HTTP/{scope.get('http_version', '1.1')}",
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': scope.get('scheme', 'http'),
            'wsgi.input': body_file,
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': True,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
        }
        client = scope.get('client')
        if client:
            environ['REMOTE_ADDR'] = client[0]
            environ['REMOTE_PORT'] = str(client[1])
        server = scope.get('server')
        if server:
            environ['SERVER_NAME'] = server[0]
            environ['SERVER_PORT'] = str(server[1])
        for name, value in scope.get('headers', []):
            key = name.decode('latin-1').upper().replace('-', '_')
            value = value.decode('latin-1')
            if key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                environ[key] = value
            else:
                environ[f'HTTP_{key}'] = value
        if 'CONTENT_LENGTH' not in environ:
            environ['wsgi.input_terminated'] = True
        return environ

    async def __call__(self, scope, receive, send):  # noqa
        if scope['type'] != 'http':
            return
        loop = asyncio.get_running_loop()
        rsock, wsock = socket.socketpair()
        rsock.setblocking(True)
        wsock.setblocking(False)
        response_started = asyncio.Event()
        response_status = {}
        response_headers = []
        response_chunks = []
        error = []

        def start_response(status, headers, exc_info=None):
            response_status['code'] = int(status.split()[0])
            response_headers.extend(
                (k.encode('latin-1'), v.encode('latin-1'))
                for k, v in headers
            )
            response_started.set()

            def write(data):
                if data:
                    response_chunks.append(bytes(data))

            return write

        def run_wsgi():
            body_file = rsock.makefile('rb')
            try:
                environ = self._build_environ(scope, body_file)
                result = self._app(environ, start_response)
                try:
                    for chunk in result:
                        if chunk:
                            response_chunks.append(bytes(chunk))
                finally:
                    if hasattr(result, 'close'):
                        result.close()
            except Exception as exc:
                error.append(exc)
            finally:
                body_file.close()
                rsock.close()

        thread = threading.Thread(target=run_wsgi, daemon=True)
        thread.start()
        try:
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    break
                body = message.get('body', b'')
                if body:
                    await loop.sock_sendall(wsock, body)
                if not message.get('more_body', False):
                    break
        finally:
            try:
                wsock.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            wsock.close()
        thread.join()
        if error:
            raise error[0]
        await send({
            'type': 'http.response.start',
            'status': response_status.get('code', 500),
            'headers': response_headers,
        })
        await send({
            'type': 'http.response.body',
            'body': b''.join(response_chunks),
            'more_body': False,
        })


@asynccontextmanager
async def lifespan(app):
    logger = logging.getLogger(__name__)
    logger.info('Girder server running')
    yield


app = Starlette(
    lifespan=lifespan,
    routes=[
        WebSocketRoute('/notifications/me', UserNotificationsSocket),
        Mount('/', app=_WSGIBridge(wsgi_app)),
    ],
)
