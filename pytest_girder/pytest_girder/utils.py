import base64
import cherrypy
import contextlib
from dataclasses import dataclass
import io
import json
import socket
from typing import Optional
import urllib.parse


def getResponseBody(response, text=True):
    """
    Returns the response body as a text type or binary string.

    :param response: The response object from the server.
    :param text: If true, treat the data as a text string, otherwise, treat
                 as binary.
    """
    data = '' if text else b''

    for chunk in response.body:
        if text and isinstance(chunk, bytes):
            chunk = chunk.decode('utf8')
        elif not text and not isinstance(chunk, bytes):
            chunk = chunk.encode('utf8')
        data += chunk

    return data


def request(path='/', method='GET', params=None, user=None,
            prefix='/api/v1', isJson=True, basicAuth=None, body=None,
            type=None, exception=False, cookie=None, token=None,
            additionalHeaders=None, useHttps=False,
            authHeader='Authorization', appPrefix='/api'):
    """
    Make an HTTP request.

    :param path: The path part of the URI.
    :type path: str
    :param method: The HTTP method.
    :type method: str
    :param params: The HTTP parameters.
    :type params: dict
    :param prefix: The prefix to use before the path.
    :param isJson: Whether the response is a JSON object.
    :param basicAuth: A string to pass with the Authorization: Basic header
                      of the form 'login:password'
    :param exception: Set this to True if a 500 is expected from this call.
    :param cookie: A custom cookie value to set.
    :param token: If you want to use an existing token to login, pass
        the token ID.
    :type token: str
    :param additionalHeaders: A list of headers to add to the
                              request.  Each item is a tuple of the form
                              (header-name, header-value).
    :param useHttps: If True, pretend to use HTTPS.
    :param authHeader: The HTTP request header to use for authentication.
    :type authHeader: str
    :param appPrefix: The CherryPy application prefix (mounted location without trailing slash)
    :type appPrefix: str
    :returns: The cherrypy response object from the request.
    """
    local = cherrypy.lib.httputil.Host('127.0.0.1', 30000)
    remote = cherrypy.lib.httputil.Host('127.0.0.1', 30001)
    headers = [('Host', '127.0.0.1'), ('Accept', 'application/json')]
    qs = fd = None

    if additionalHeaders:
        headers.extend(additionalHeaders)

    if isinstance(body, str):
        body = body.encode('utf8')

    if params:
        qs = urllib.parse.urlencode(params)

    if params and body:
        # In this case, we are forced to send params in query string
        fd = io.BytesIO(body)
        headers.append(('Content-Type', type))
        headers.append(('Content-Length', '%d' % len(body)))
    elif method in ['POST', 'PUT', 'PATCH'] or body:
        if type:
            qs = body
        elif params:
            qs = qs.encode('utf8')

        headers.append(('Content-Type', type or 'application/x-www-form-urlencoded'))
        headers.append(('Content-Length', '%d' % len(qs or b'')))
        fd = io.BytesIO(qs or b'')
        qs = None

    app = cherrypy.tree.apps[appPrefix]
    request, response = app.get_serving(
        local, remote, 'http' if not useHttps else 'https', 'HTTP/1.1')
    request.show_tracebacks = True

    headers = buildHeaders(headers, cookie, user, token, basicAuth, authHeader)

    url = prefix + path
    try:
        response = request.run(method, url, qs, 'HTTP/1.1', headers, fd)
    finally:
        if fd:
            fd.close()

    if isJson:
        body = getResponseBody(response)
        try:
            response.json = json.loads(body)
        except ValueError:
            raise AssertionError('Did not receive JSON response')

    if not exception and response.output_status.startswith(b'500'):
        raise AssertionError('Internal server error: %s' %
                             getResponseBody(response))

    return response


def buildHeaders(headers, cookie, user, token, basicAuth, authHeader):
    from girder.models.token import Token

    headers = headers[:]
    if cookie is not None:
        headers.append(('Cookie', cookie))

    if user is not None:
        token = Token().createToken(user)
        headers.append(('Girder-Token', str(token['_id'])))
    elif token is not None:
        if isinstance(token, dict):
            headers.append(('Girder-Token', token['_id']))
        else:
            headers.append(('Girder-Token', token))

    if basicAuth is not None:
        auth = base64.b64encode(basicAuth.encode('utf8'))
        headers.append((authHeader, 'Basic %s' % auth.decode()))

    return headers


def uploadFile(name, contents, user, parent, parentType='folder',
               mimeType=None):
    """
    Upload a file.

    :param name: The name of the file.
    :type name: str
    :param contents: The file contents
    :type contents: str
    :param user: The user performing the upload.
    :type user: dict
    :param parent: The parent document.
    :type parent: dict
    :param parentType: The type of the parent ("folder" or "item")
    :type parentType: str
    :param mimeType: Explicit MIME type to set on the file.
    :type mimeType: str
    :returns: The file that was created.
    :rtype: dict
    """
    mimeType = mimeType or 'application/octet-stream'
    upload = request(path='/file', method='POST', user=user,
                     params={
                         'parentType': parentType,
                         'parentId': str(parent['_id']),
                         'name': name,
                         'size': len(contents),
                         'mimeType': mimeType
                     })

    resp = request(path='/file/chunk', method='POST', user=user,
                   body=contents,
                   params={
                       'uploadId': upload.json['_id'],
                       'offset': 0
                   },
                   type='text/plain')

    return resp.json


def _findFreePort():
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('', 0))
        return sock.getsockname()[1]


@dataclass
class ServerFixture:
    request = staticmethod(request)
    uploadFile = staticmethod(uploadFile)
    serverRoot: cherrypy._cptree.Tree
    boundPort: Optional[int] = None

    def __getattr__(self, name):
        return getattr(self.serverRoot, name)


@contextlib.contextmanager
def serverContext(plugins=None, bindPort=False) -> ServerFixture:
    from girder import plugin
    from girder.api import docs
    from girder.utility.server import create_app
    from girder.constants import ServerMode

    if plugins is None:
        # By default, pass "[]" to "plugins", disabling any installed plugins
        plugins = []
    app_info = create_app(mode=ServerMode.TESTING)
    plugin._loadPlugins(app_info, plugins)

    server_fixture = ServerFixture(serverRoot=app_info['serverRoot'])

    cherrypy.tree = app_info['serverRoot']
    cherrypy.server.unsubscribe()
    if bindPort:
        cherrypy.server.subscribe()
        port = _findFreePort()
        cherrypy.config['server.socket_port'] = port
        server_fixture.boundPort = port
        # This is needed if cherrypy started once on another port
        cherrypy.server.socket_port = port
    cherrypy.config.update({
        'environment': 'embedded',
        'log.screen': False,
        'request.throw_errors': True
    })
    cherrypy.engine.start()

    try:
        yield server_fixture
    finally:
        cherrypy.engine.stop()
        cherrypy.engine.exit()
        cherrypy.tree.apps = {}
        # This is needed to allow cherrypy to restart on another port
        cherrypy.server.httpserver = None
        docs.routes.clear()
