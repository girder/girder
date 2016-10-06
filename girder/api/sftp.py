#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2016 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import os
import paramiko
import six
import stat
import time

from girder import logger
from girder.models.model_base import AccessException, ValidationException
from girder.utility.path import lookUpPath, NotFoundException
from girder.utility.model_importer import ModelImporter
from six.moves import socketserver

DEFAULT_PORT = 8022


def _handleErrors(fun):
    @six.wraps(fun)
    def wrapped(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except NotFoundException:
            return paramiko.SFTP_NO_SUCH_FILE
        except ValidationException:
            return paramiko.SFTP_FAILURE
        except AccessException:
            return paramiko.SFTP_PERMISSION_DENIED
        except Exception:
            logger.exception('SFTP server internal error')

    return wrapped


def _getFileSize(file):
    if file.get('assetstoreId'):
        return file['size']
    elif file.get('linkUrl'):
        return len(file['linkUrl'])


class _FileHandle(paramiko.SFTPHandle, ModelImporter):
    def __init__(self, file):
        """
        Create a file-like object representing a file blob stored in Girder.

        :param file: The file object being opened.
        :type file: dict
        """
        super(_FileHandle, self).__init__()

        self.file = file

    def read(self, offset, length):
        stream = self.model('file').download(
            self.file, headers=False, offset=offset, endByte=offset + length)
        return b''.join(stream())

    def stat(self):
        info = paramiko.SFTPAttributes()
        info.filename = self.file['name'].encode('utf8')
        info.st_mtime = time.mktime(self.file['created'].timetuple())
        info.st_mode = 0o777 | stat.S_IFREG
        info.st_size = _getFileSize(self.file)

        return info

    def close(self):
        return paramiko.SFTP_OK


class _SftpServerAdapter(paramiko.SFTPServerInterface, ModelImporter):
    def __init__(self, server, *args, **kwargs):
        self.server = server
        paramiko.SFTPServerInterface.__init__(self, server, *args, **kwargs)

    def _list(self, model, document):
        entries = []
        if model in ('collection', 'user', 'folder'):
            for folder in self.model('folder').childFolders(
                    parent=document, parentType=model, user=self.server.girderUser):
                info = paramiko.SFTPAttributes()
                info.st_size = 0
                info.st_mode = 0o777 | stat.S_IFDIR
                info.st_mtime = time.mktime(folder['updated'].timetuple())
                info.filename = folder['name'].encode('utf8')
                entries.append(info)

        if model == 'folder':
            for item in self.model('folder').childItems(document):
                info = paramiko.SFTPAttributes()
                info.st_size = 0
                info.st_mode = 0o777 | stat.S_IFDIR
                info.st_mtime = time.mktime(item['updated'].timetuple())
                info.filename = item['name'].encode('utf8')
                entries.append(info)
        elif model == 'item':
            for file in self.model('item').childFiles(document):
                info = paramiko.SFTPAttributes()
                info.st_mtime = time.mktime(file['created'].timetuple())
                info.st_mode = 0o777 | stat.S_IFREG
                info.st_size = _getFileSize(file)
                info.filename = file['name'].encode('utf8')
                entries.append(info)

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
        elif path == '/user':
            for user in self.model('user').list(user=self.server.girderUser):
                info = paramiko.SFTPAttributes()
                info.st_size = 0
                info.st_mode = 0o777 | stat.S_IFDIR
                info.filename = user['login'].encode('utf8')
                entries.append(info)
        elif path == '/collection':
            for collection in self.model('collection').list(user=self.server.girderUser):
                info = paramiko.SFTPAttributes()
                info.st_size = 0
                info.st_mode = 0o777 | stat.S_IFDIR
                info.filename = collection['name'].encode('utf8')
                entries.append(info)
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
        obj = lookUpPath(path, filter=False, user=self.server.girderUser)

        doc = obj['document']
        info = paramiko.SFTPAttributes()
        info.filename = doc['name'].encode('utf8')

        if 'updated' in doc:
            info.st_mtime = time.mktime(doc['updated'].timetuple())
        elif 'created' in doc:
            info.st_mtime = time.mktime(doc['created'].timetuple())

        if obj['model'] == 'file':
            info.st_mode = 0o777 | stat.S_IFREG
            info.st_size = _getFileSize(doc)
        else:
            info.st_mode = 0o777 | stat.S_IFDIR
            info.st_size = 0

        return info

    def lstat(self, path):
        return self.stat(path)

    @_handleErrors
    def mkdir(self, path, attrs):
        """
        Uncomment this implementation once we are ready to support write ops.
        parent, dirname = os.path.split(path)
        obj = lookUpPath(parent, filter=False, user=self.server.girderUser)
        parentType, parent = obj['model'], obj['document']

        if parentType in ('user', 'collection', 'folder'):
            self.model(parentType).requireAccess(
                parent, user=self.server.girderUser, level=AccessType.WRITE)
            self.model('folder').createFolder(
                parent, dirname, parentType=parentType, creator=self.server.girderUser,
                reuseExisting=True)
            return paramiko.SFTP_OK
        else:
            raise ValidationException('Invalid parent type %s.' % obj['model'])
        """
        return paramiko.SFTP_OP_UNSUPPORTED


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


class _ServerAdapter(paramiko.ServerInterface, ModelImporter):
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
        return paramiko.AUTH_FAILED

    def check_auth_password(self, username, password):
        if username.lower() == 'anonymous':
            return paramiko.AUTH_SUCCESSFUL

        try:
            self.girderUser = self.model('user').authenticate(username, password)
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


def _main():  # pragma: no cover
    """
    This is the entrypoint of the girder-sftpd program. It should not be
    called from python code.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog='girder-sftpd', description='Run the Girder SFTP service.')
    parser.add_argument(
        '-i', '--identity-file', required=False, help='path to identity (private key) file')
    parser.add_argument('-p', '--port', required=False, default=DEFAULT_PORT, type=int)

    args = parser.parse_args()

    keyFile = args.identity_file or os.path.expanduser(os.path.join('~', '.ssh', 'id_rsa'))
    hostKey = paramiko.RSAKey.from_private_key_file(keyFile)

    server = SftpServer(('localhost', args.port), hostKey)

    try:
        server.serve_forever()
    except (SystemExit, KeyboardInterrupt):
        server.server_close()


if __name__ == '__main__':  # pragma: no cover
    _main()
