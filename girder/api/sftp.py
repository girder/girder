# -*- coding: utf-8 -*-
from functools import wraps
import paramiko
import socketserver
import stat
import time

from girder import logger
from girder.exceptions import AccessException, ValidationException, ResourcePathNotFound
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.user import User
from girder.utility.path import lookUpPath
from girder.utility.model_importer import ModelImporter

MAX_BUF_LEN = 10 * 1024 * 1024


def _handleErrors(fun):
    @wraps(fun)
    def wrapped(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except ResourcePathNotFound:
            return paramiko.SFTP_NO_SUCH_FILE
        except ValidationException:
            return paramiko.SFTP_FAILURE
        except AccessException:
            return paramiko.SFTP_PERMISSION_DENIED
        except Exception:
            logger.exception('SFTP server internal error')
            return paramiko.SFTP_FAILURE

    return wrapped


def _getFileSize(file):
    return file.get('size', len(file.get('linkUrl', '')))


def _stat(doc, model):
    info = paramiko.SFTPAttributes()

    if model == 'user':
        info.filename = doc['login'].encode('utf8')
    else:
        info.filename = doc['name'].encode('utf8')

    if 'updated' in doc:
        info.st_mtime = time.mktime(doc['updated'].timetuple())
    elif 'created' in doc:
        info.st_mtime = time.mktime(doc['created'].timetuple())

    if model == 'file':
        info.st_mode = 0o777 | stat.S_IFREG
        info.st_size = _getFileSize(doc)
    else:
        info.st_mode = 0o777 | stat.S_IFDIR
        info.st_size = 0

    return info


class _FileHandle(paramiko.SFTPHandle):
    def __init__(self, file):
        """
        Create a file-like object representing a file blob stored in Girder.

        :param file: The file object being opened.
        :type file: dict
        """
        super(_FileHandle, self).__init__()

        self.file = file
        self._handle = File().open(file)

    def read(self, offset, length):
        if length > MAX_BUF_LEN:
            raise IOError(
                'Requested chunk length (%d) is larger than the maximum allowed.' % length)

        if offset != self._handle.tell() and offset < self.file['size']:
            self._handle.seek(offset)

        return self._handle.read(length)

    def stat(self):
        return _stat(self.file, 'file')

    def close(self):
        self._handle.close()
        return paramiko.SFTP_OK


class _SftpServerAdapter(paramiko.SFTPServerInterface):
    def __init__(self, server, *args, **kwargs):
        self.server = server
        paramiko.SFTPServerInterface.__init__(self, server, *args, **kwargs)

    def _list(self, model, document):
        entries = []
        if model in ('collection', 'user', 'folder'):
            for folder in Folder().childFolders(
                    parent=document, parentType=model, user=self.server.girderUser):
                entries.append(_stat(folder, 'folder'))

        if model == 'folder':
            for item in Folder().childItems(document):
                entries.append(_stat(item, 'item'))
        elif model == 'item':
            for file in Item().childFiles(document):
                entries.append(_stat(file, 'file'))

        return entries

    @_handleErrors
    def list_folder(self, path):
        path = path.rstrip('/')
        entries = []

        if path == '':
            for model in ('collection', 'user'):
                info = paramiko.SFTPAttributes()
                info.st_size = 0
                info.st_mode = 0o777 | stat.S_IFDIR
                info.filename = model.encode('utf8')
                entries.append(info)
        elif path in ('/user', '/collection'):
            model = path[1:]
            for doc in ModelImporter.model(model).list(user=self.server.girderUser):
                entries.append(_stat(doc, model))
        else:
            obj = lookUpPath(path, filter=False, user=self.server.girderUser)
            return self._list(obj['model'], obj['document'])

        return entries

    @_handleErrors
    def open(self, path, flags, attr):
        obj = lookUpPath(path, filter=False, user=self.server.girderUser)

        if obj['model'] != 'file':
            return paramiko.SFTP_NO_SUCH_FILE

        return _FileHandle(obj['document'])

    @_handleErrors
    def stat(self, path):
        path = path.rstrip('/')
        if path == '':
            info = paramiko.SFTPAttributes()
            info.st_size = 0
            info.st_mode = 0o777 | stat.S_IFDIR
            info.filename = '/'
            return info
        elif path in ('/user', '/collection'):
            info = paramiko.SFTPAttributes()
            info.st_size = 0
            info.st_mode = 0o777 | stat.S_IFDIR
            info.filename = path[1:]
            return info

        obj = lookUpPath(path, filter=False, user=self.server.girderUser)
        return _stat(obj['document'], obj['model'])

    def lstat(self, path):
        return self.stat(path)


class _SftpRequestHandler(socketserver.BaseRequestHandler):
    timeout = 60
    auth_timeout = 60

    def setup(self):
        self.transport = paramiko.Transport(self.request)

        securityOptions = self.transport.get_security_options()
        securityOptions.digests = ('hmac-sha1', 'hmac-sha2-256')
        securityOptions.compression = ('zlib@openssh.com', 'none')

        self.transport.add_server_key(self.server.hostKey)
        self.transport.set_subsystem_handler('sftp', paramiko.SFTPServer, _SftpServerAdapter)

    def handle(self):
        self.transport.start_server(server=_ServerAdapter())


class _ServerAdapter(paramiko.ServerInterface):
    def __init__(self, *args, **kwargs):
        paramiko.ServerInterface.__init__(self, *args, **kwargs)
        self.girderUser = None

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def get_allowed_auths(self, username):
        return 'password'

    def check_auth_none(self, username):
        if username.lower() == 'anonymous':
            return paramiko.AUTH_SUCCESSFUL
        else:
            return paramiko.AUTH_FAILED

    def check_auth_password(self, username, password):
        if username.lower() == 'anonymous':
            return paramiko.AUTH_SUCCESSFUL

        try:
            self.girderUser = User().authenticate(username, password, otpToken=True)
            return paramiko.AUTH_SUCCESSFUL
        except AccessException:
            return paramiko.AUTH_FAILED


class SftpServer(socketserver.ThreadingTCPServer):

    allow_reuse_address = True

    def __init__(self, address, hostKey):
        """
        Creates but does not start a Girder SFTP server.

        :param address: Hostname and port for the server to bind to.
        :type address: (str, int) tuple
        :param hostKey: Private key for the server to use.
        :type hostKey: paramiko.RSAKey
        """
        self.hostKey = hostKey
        paramiko.Transport.load_server_moduli()

        socketserver.TCPServer.__init__(self, address, _SftpRequestHandler)

    def shutdown_request(self, request):
        pass
