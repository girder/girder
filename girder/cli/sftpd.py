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

import click
import os
import paramiko
import sys

from girder import logprint
from girder.api.sftp import SftpServer

DEFAULT_PORT = 8022


@click.command(name='sftpd', short_help='Run the Girder SFTP service.',
               help='Run the Girder SFTP service.')
@click.option('-i', '--identity-file', show_default=True,
              default=os.path.expanduser(os.path.join('~', '.ssh', 'id_rsa')),
              help='The identity (private key) file to use')
@click.option('-H', '--host', show_default=True, default='localhost',
              help='The interface to bind to')
@click.option('-p', '--port', show_default=True, default=DEFAULT_PORT, type=int,
              help='The port to bind to')
def main(identity_file, port, host):
    """
    This is the entrypoint of the girder sftpd program. It should not be
    called from python code.
    """
    try:
        hostKey = paramiko.RSAKey.from_private_key_file(identity_file)
    except paramiko.ssh_exception.PasswordRequiredException:
        logprint.error(
            'Error: encrypted key files are not supported (%s).' % identity_file, file=sys.stderr)
        sys.exit(1)

    server = SftpServer((host, port), hostKey)
    logprint.info('Girder SFTP service listening on %s:%d.' % (host, port))

    try:
        server.serve_forever()
    except (SystemExit, KeyboardInterrupt):
        server.server_close()
