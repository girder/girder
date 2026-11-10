import base64
import cherrypy
import contextlib
import email
import io
import json
import queue
import socket
import socketserver
import threading
import time
import urllib.parse


class _MockSmtpHandler(socketserver.StreamRequestHandler):
    """
    Handle a single SMTP session, accepting every message and placing its data
    on the server's mail queue.  Only the subset of SMTP used by smtplib to
    send unauthenticated, unencrypted mail is implemented.
    """

    def _reply(self, line):
        self.wfile.write(line.encode('ascii') + b'\r\n')

    def handle(self):
        self._reply('220 localhost Mock SMTP server ready')
        while True:
            line = self.rfile.readline()
            if not line:
                return
            command = line.strip().split(b' ', 1)[0].upper()
            if command in (b'HELO', b'EHLO'):
                self._reply('250 localhost')
            elif command in (b'MAIL', b'RCPT', b'RSET', b'NOOP'):
                self._reply('250 OK')
            elif command == b'DATA':
                self._reply('354 End data with <CR><LF>.<CR><LF>')
                lines = []
                while True:
                    line = self.rfile.readline()
                    if not line:
                        return
                    if line in (b'.\r\n', b'.\n'):
                        break
                    # Undo dot-stuffing (RFC 5321 section 4.5.2)
                    if line.startswith(b'.'):
                        line = line[1:]
                    lines.append(line)
                self.server.mailQueue.put(b''.join(lines))
                self._reply('250 OK')
            elif command == b'QUIT':
                self._reply('221 Bye')
                return
            else:
                self._reply('502 Command not implemented')


class _MockSmtpServer(socketserver.ThreadingTCPServer):
    daemon_threads = True

    def __init__(self, address):
        self.mailQueue = queue.Queue()
        super().__init__(address, _MockSmtpHandler)


class MockSmtpReceiver:
    def __init__(self):
        self.address = None
        self.smtp = None
        self.thread = None

    def start(self):
        """
        Start the mock SMTP server on an available port.  The bound host and
        port are available as the ``address`` attribute.
        """
        self.smtp = _MockSmtpServer(('localhost', 0))
        self.address = ('localhost', self.smtp.server_address[1])
        self.thread = threading.Thread(target=self.smtp.serve_forever, kwargs={
            'poll_interval': 0.1}, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the mock STMP server"""
        self.smtp.shutdown()
        self.smtp.server_close()
        self.thread.join()

    def getMail(self, parse=False):
        """
        Return the message at the front of the queue.
        Raises Queue.Empty exception if there are no messages.

        :param parse: Whether to parse the email into an email.message.Message
            object. If False, just returns the raw email string.
        :type parse: bool
        """
        msg = self.smtp.mailQueue.get(block=False)

        if parse:
            if isinstance(msg, bytes):
                return email.message_from_bytes(msg)
            else:
                return email.message_from_string(msg)
        else:
            return msg

    def isMailQueueEmpty(self):
        """Return whether or not the mail queue is empty"""
        return self.smtp.mailQueue.empty()

    def waitForMail(self, timeout=10):
        """
        Waits for mail to appear on the queue. Returns "True" as soon as the
        queue is not empty, or "False" if the timeout was reached before any
        mail appears.

        :param timeout: Timeout in seconds.
        :type timeout: float
        """
        startTime = time.time()
        while True:
            if not self.isMailQueueEmpty():
                return True
            if time.time() > startTime + timeout:
                return False
            time.sleep(0.1)


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
            authHeader='Authorization', appPrefix=''):
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


@contextlib.contextmanager
def serverContext(plugins=None, bindPort=False):
    # The event daemon cannot be restarted since it is a threading.Thread
    # object, however all references to girder.events.daemon are a singular
    # global daemon due to its side effect on import. We have to hack around
    # this by creating a unique event daemon each time we startup the server
    # and assigning it to the global.
    import girder.events
    from girder.api import docs
    from girder.utility.server import setup as setupServer
    from girder.constants import ServerMode

    girder.events.daemon = girder.events.AsyncEventsThread()

    if plugins is None:
        # By default, pass "[]" to "plugins", disabling any installed plugins
        plugins = []
    server = setupServer(mode=ServerMode.TESTING, plugins=plugins)
    server.request = request
    server.uploadFile = uploadFile
    cherrypy.server.unsubscribe()
    if bindPort:
        cherrypy.server.subscribe()
        port = _findFreePort()
        cherrypy.config['server.socket_port'] = port
        server.boundPort = port
        # This is needed if cherrypy started once on another port
        cherrypy.server.socket_port = port
    cherrypy.config.update({'environment': 'embedded',
                            'log.screen': False,
                            'request.throw_errors': True})
    cherrypy.engine.start()

    try:
        yield server
    finally:
        cherrypy.engine.unsubscribe('start', girder.events.daemon.start)
        cherrypy.engine.unsubscribe('stop', girder.events.daemon.stop)
        cherrypy.engine.stop()
        cherrypy.engine.exit()
        # Since the daemon was unsubscribed from the engine, stop it explicitly
        # so its thread doesn't linger after the test.
        girder.events.daemon.stop()
        cherrypy.tree.apps = {}
        # This is needed to allow cherrypy to restart on another port
        cherrypy.server.httpserver = None
        docs.routes.clear()
