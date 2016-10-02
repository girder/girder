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
from girder.constants import AccessType
from girder.models.model_base import AccessException, ValidationException
from girder.utility.path import lookUpPath, NotFoundException
from girder.utility.model_importer import ModelImporter
from six.moves import socketserver, StringIO

DEFAULT_PORT = 8022
DEFAULT_KEY = paramiko.RSAKey.from_private_key(StringIO("""-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAwdH5tlaZu52adYvW57DcAFknzOKX8+/axDmQdTcg1HwEOnT2
TMSFGciwUQMmya+0i23ZOUtZQutj8fb66szrBZ7qpIvSG6TRyxGuM6PkfAUcBCHO
TGFzaJPnnvUXC8dlxoUIdBaUCmSblvj2q2CTNy53ybAmiiSpahjvBO16pvjbNn+i
EGucSQn71OTMhoSOWtS/VcJC6JPd6kxSdl1EiESbOrjAdNDKMBnfYCkxPG4ulAqe
y5jpfgQiUC0Q3CoWbj/ybAv73JsFndPcpvI8n5EsXeptuWI4CXSorYOuVwURLuzP
z1PkI4ZsYnSnuQG/GReAZnwVDaVJ/uhYMMs1sQIDAQABAoIBADKOmguFBW7aCntU
8cbX7Fsu5mHcTXS1ASSkO1lH+wlSHCw/bCvUKz/xiIRpRQnhCkBAdCQs0mjRS+3G
1ea/cyKxNFWdnz3UvWCyCPWxb50mHAu74bssxFToF8fv+IX7CkJBW1YkuZMIcUlt
QbKsa1o+hcKXb0YjkAl73YU0iQTaet7B1x1X0qkVPEWWURTg3z65TNI96t8p28dh
4HgEoU0Jtfsfzb7u1H4/m3Q28J1S+cTkER/VIgLzMeYXr2MooIQc3QAMXATpXkhM
y6u0LYh+kW1XD4ZnyzTp49BMf76rS8VhsYN6f+jLhJUf/5O+m8NFGuCq15TFyQAH
vMBxPRECgYEA4+fxYuuOq+SilYpejD4EMwvrClixHOfTojlnAyUaJZSnyVp/Y4l+
QmFmbNpfRKN1fv24e9f9CmA8nd5A3kxBjJFhzaaxbFG+jI47fqOu9NadXPHaxvyq
BI2aHx4sqp/Z/ct/klht5hxD8UFMRFbaaLYAojKg1nL0g/88wwwN9LUCgYEA2bZh
873OGT7sNXHin2rXD5XEYXqjLy51hed4ZdtJXFrKhg8ozWqaOZ79GXustdRanzTV
zDeTweI0hg7adbKyBNeuQF8VSOK6ws2wPPCuUbQTVYaepqPuT+VhzAB1GVJ1uF/T
YxgqXOvg9QwnZ4Fjlv3b/52R89bTP+Yr6GcQdo0CgYAvLQ38igIodtVo2xGjOhso
bekjZSSUdTCLvhIixoVZDiKFPaRs+EMYfozzL2jVDnj95otPp3ALu8wQabdHzMUs
0dNK/JxxbaJh+fc6yasnp10/phjBY//VnXIvytE4KIq5TGyF4KQvI960i+27n7bq
QfJzoMNGYNlYkXcEcPRamQKBgQCVCYWElirAnZKWA6BgAYO3547ILGwJoIRTZmHF
WJif4IdDvpzwAkoRqAUbrM5Oq1BeLI0vf9xmnbPXEdP7PpkfN4bSCkVH3+557NT4
4spypBOYOM/iw9YgW6bXQHjpHMn5rZ/H9oMJmXAmUGupL6o9cwtnsTZ49lcnJypn
riZXAQKBgQCgiJ/A11HX7fUgFzBB9no2Sy1hS3u1Ld35nZf7RDegVoEn/UdWdOxn
H2T9t0EzIoSqkfPRrsqN8sv/TMIohS6frOpBojEvwUs5mxjVwswq/QgBSV2FqYck
VeccLgZzTSMNzCDMbtM+zGG5WktzFojrMIhfD0SM3CB3jECF+Dfdtg==
-----END RSA PRIVATE KEY-----
"""))


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
            for model in ('user', 'collection'):
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
        if username == 'anonymous':
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_auth_password(self, username, password):
        try:
            self.girderUser = self.model('user').authenticate(username, password)
            return paramiko.AUTH_SUCCESSFUL
        except AccessException:
            return paramiko.AUTH_FAILED


class _SftpServer(socketserver.ThreadingTCPServer):

    allow_reuse_address = True

    def __init__(self, address, hostKey=None):
        self.hostKey = hostKey or DEFAULT_KEY
        paramiko.Transport.load_server_moduli()

        socketserver.TCPServer.__init__(self, address, _SftpRequestHandler)

    def shutdown_request(self, request):
        pass


def startServer(port=DEFAULT_PORT):
    """
    Start the Girder SFTP server on the specified port.
    """
    server = _SftpServer(('localhost', port))
    try:
        server.serve_forever()
    except (SystemExit, KeyboardInterrupt):
        server.server_close()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog='girder-sftpd', description='Run the Girder SFTP service.')
    parser.add_argument('-p', '--port', required=False, default=DEFAULT_PORT, type=int)

    args = parser.parse_args()
    startServer(port=args.port)


if __name__ == '__main__':
    main()
