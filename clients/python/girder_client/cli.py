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
from girder_client import GirderClient


class GirderCli(GirderClient):
    """
    A command line Python client for interacting with a Girder instance's
    RESTful api, specifically for performing uploads into a Girder instance.
    """

    def __init__(self, username, password, host=None, port=None, apiRoot=None,
                 scheme=None, apiUrl=None, apiKey=None):
        """
        Initialization function to create a GirderCli instance, will attempt
        to authenticate with the designated Girder instance. Aside from username, password,
        and apiKey, all other kwargs are passed directly through to the
        :py:class:`girder_client.GirderClient` base class constructor.

        :param username: username to authenticate to Girder instance.
        :param password: password to authenticate to Girder instance, leave
            this blank to be prompted.
        """
        super(GirderCli, self).__init__(
            host=host, port=port, apiRoot=apiRoot, scheme=scheme, apiUrl=apiUrl)
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

subparsers = parser.add_subparsers(
    title='subcommands', dest='subcommand', description='Valid subcommands')
subparsers.required = True

# Arguments shared by multiple subcommands (these are ordered)
_commonArgs = [
    ('--parent-type', dict(
        required=False, default='folder',
        help='type of Girder parent target, one of (collection, folder, user)')),
    ('parent_id', dict(help='id of Girder parent target')),
    ('local_folder', dict(help='path to local target folder'))
]

downloadParser = subparsers.add_parser('download', description='Download files from Girder')

localsyncParser = subparsers.add_parser(
    'localsync', description='Synchronize local folder with remote Girder folder')

uploadParser = subparsers.add_parser('upload', description='Upload files to Girder')
uploadParser.add_argument(
    '--leaf-folders-as-items', required=False, action='store_true',
    help='upload all files in leaf folders to a single Item named after the folder')
uploadParser.add_argument(
    '--reuse', required=False, action='store_true',
    help='use existing items of same name at same location or create a new one')
uploadParser.add_argument(
    '--dry-run', required=False, action='store_true',
    help='will not write anything to Girder, only report what would happen')
uploadParser.add_argument(
    '--blacklist', required=False, default='', help='comma-separated list of filenames to ignore')

# For now, all subcommands conveniently share all the common options
for name, kwargs in _commonArgs:
    uploadParser.add_argument(name, **kwargs)
    downloadParser.add_argument(name, **kwargs)
    localsyncParser.add_argument(name, **kwargs)


def main():
    args = parser.parse_args()

    gc = GirderCli(
        args.username, args.password, host=args.host, port=args.port, apiRoot=args.api_root,
        scheme=args.scheme, apiUrl=args.api_url, apiKey=args.api_key)

    if args.subcommand == 'upload':
        gc.upload(
            args.local_folder, args.parent_id, args.parent_type,
            leafFoldersAsItems=args.leaf_folders_as_items, reuseExisting=args.reuse,
            blacklist=args.blacklist.split(','), dryRun=args.dry_run)
    elif args.subcommand == 'download':
        gc.downloadResource(args.parent_id, args.local_folder, args.parent_type)
    elif args.subcommand == 'localsync':
        if args.parent_type != 'folder':
            raise Exception('localsync command only accepts parent-type of folder')

        gc.loadLocalMetadata(args.local_folder)
        gc.downloadFolderRecursive(args.parent_id, args.local_folder, sync=True)
        gc.saveLocalMetadata(args.local_folder)

if __name__ == '__main__':
    main()  # pragma: no cover
