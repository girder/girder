#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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

import argparse
import sys
from six import add_metaclass, string_types
from girder_client import GirderClient


class GirderCli(GirderClient):
    """
    A command line Python client for interacting with a Girder instance's
    RESTful api, specifically for performing uploads into a Girder instance.
    """

    def __init__(self, username, password, dryrun, blacklist,
                 host=None, port=None, apiRoot=None, scheme=None, apiUrl=None,
                 apiKey=None):
        """initialization function to create a GirderCli instance, will attempt
        to authenticate with the designated Girder instance. Aside from username
        and password, all other kwargs are passed directly through to the
        :py:class:`girder_client.GirderClient` base class constructor.

        :param username: username to authenticate to Girder instance.
        :param password: password to authenticate to Girder instance, leave
            this blank to be prompted.
        """
        GirderClient.__init__(self, host=host, port=port,
                              apiRoot=apiRoot, scheme=scheme, dryrun=dryrun,
                              blacklist=blacklist, apiUrl=apiUrl)
        interactive = password is None

        if apiKey:
            self.authenticate(apiKey=apiKey)
        elif username:
            self.authenticate(username, password, interactive=interactive)


parser = argparse.ArgumentParser(
    prog='girder-cli', description='Perform common Girder CLI operations.')
parser.add_argument('--username', required=False, default=None)
parser.add_argument('--password', required=False, default=None)
parser.add_argument('--api-key', required=False, default=None)
parser.add_argument('--api-url', required=False, default=None,
                    help='full URL to the RESTful API of a Girder server')
parser.add_argument('--scheme', required=False, default=None)
parser.add_argument('--host', required=False, default=None)
parser.add_argument('--port', required=False, default=None)
parser.add_argument('--api-root', required=False, default=None,
                    help='relative path to the Girder REST API')
parser.add_argument('--blacklist', default='', required=False,
                    help='comma separated list of filenames to ignore'),
parser.add_argument('--dryrun', action='store_true',
                    help='will not write anything to Girder, only report'
                    ' on what would happen'),


subparsers = parser.add_subparsers(title='subcommands',
                                   dest='subcommands',
                                   description='Valid subcommands',)
_COMMON_OPTIONS = dict(
    reuse=dict(longname='--reuse', action='store_true',
               help='use existing items of same name at same location'
                    ' or create a new one'),
    leaf_folders_as_items=dict(
        longname='--leaf-folders-as-items', required=False,
        action='store_true',
        help='upload all files in leaf folders'
             'to a single Item named after the folder'),
    parent_type=dict(
        longname='--parent-type', required=False, default='folder',
        help='type of Girder parent target, one of '
             '(collection, folder, user)'),
    parent_id=dict(short='parent_id', help='id of Girder parent target'),
    local_folder=dict(short='local_folder',
                      help='path to local target folder'),
)


class GirderCommandSubtype(type):
    def __init__(cls, name, b, d):
        type.__init__(cls, name, b, d)
        if cls.name:
            sc = subparsers.add_parser(
                cls.name, description=cls.description,
                help=cls.description)
            sc.set_defaults(func=cls.run)
            for arg in cls.args:
                if isinstance(arg, string_types):
                    arg = _COMMON_OPTIONS[arg].copy()
                argc = dict(arg.items())
                argnames = []
                if 'short' in argc:
                    argnames.append(argc.pop('short'))
                if 'longname' in argc:
                    argnames.append(argc.pop('longname'))
                sc.add_argument(*argnames, **argc)


@add_metaclass(GirderCommandSubtype)
class GirderCommand(object):
    args = ()
    name = None
    description = ''
    gc = None

    @classmethod
    def run(cls, args):
        self = cls()
        self(args)

    def _set_client(self, args):
        self.gc = GirderCli(
            args.username, args.password, bool(args.dryrun),
            args.blacklist.split(','), host=args.host, port=args.port,
            apiRoot=args.api_root, scheme=args.scheme,
            apiUrl=args.api_url, apiKey=args.api_key)


class GirderUploadCommand(GirderCommand):
    name = 'upload'
    description = 'Upload files to Girder'
    args = ('reuse', 'leaf_folders_as_items',
            'parent_type', 'parent_id', 'local_folder')

    def __call__(self, args):
        self._set_client(args)
        self.gc.upload(
            args.local_folder, args.parent_id, args.parent_type,
            leaf_folders_as_items=args.leaf_folders_as_items,
            reuse_existing=args.reuse)


class GirderDownloadCommand(GirderCommand):
    name = 'download'
    description = 'Download files from Girder'
    args = ('parent_type', 'parent_id', 'local_folder')

    def __call__(self, args):
        if args.parent_type != 'folder':
            print('download command only accepts parent-type of folder')
            sys.exit(0)

        self._set_client(args)
        self.gc.downloadFolderRecursive(args.parent_id, args.local_folder)


class GirderLocalsyncCommand(GirderCommand):
    name = 'localsync'
    description = 'Synchronize local folder with remote Girder folder'
    args = ('parent_type', 'parent_id', 'local_folder')

    def __call__(self, args):
        if args.parent_type != 'folder':
            print('localsync command only accepts parent-type of folder')
            sys.exit(0)

        self._set_client(args)
        self.gc.loadLocalMetadata(args.local_folder)
        self.gc.downloadFolderRecursive(args.parent_id, args.local_folder,
                                        sync=True)
        self.gc.saveLocalMetadata(args.local_folder)


def main():
    args = parser.parse_args()
    try:
        getattr(args, "func")
    except AttributeError:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()  # pragma: no cover
