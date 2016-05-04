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


def main():
    parser = argparse.ArgumentParser(
        description='Perform common Girder CLI operations.')
    parser.add_argument(
        '--reuse', action='store_true',
        help='use existing items of same name at same location or create a new'
        ' one')
    parser.add_argument(
        '--blacklist', default='', required=False,
        help='comma separated list of filenames to ignore')
    parser.add_argument(
        '--dryrun', action='store_true',
        help='will not write anything to Girder, only report on what would '
        'happen')
    parser.add_argument('--api-url', required=False, default=None,
                        help='full URL to the RESTful API of a Girder server')
    parser.add_argument('--username', required=False, default=None)
    parser.add_argument('--password', required=False, default=None)
    parser.add_argument('--api-key', required=False, default=None)
    parser.add_argument('--scheme', required=False, default=None)
    parser.add_argument('--host', required=False, default=None)
    parser.add_argument('--port', required=False, default=None)
    parser.add_argument('--api-root', required=False, default=None,
                        help='relative path to the Girder REST API')
    parser.add_argument('-c', default='upload', choices=['upload', 'download'],
                        help='command to run')
    parser.add_argument('parent_id', help='id of Girder parent target')
    parser.add_argument('--parent-type', required=False, default='folder',
                        help='type of Girder parent target, one of ' +
                        '(collection, folder, user)')
    parser.add_argument('local_folder', help='path to local target folder')
    parser.add_argument('--leaf-folders-as-items', required=False,
                        action='store_true',
                        help='upload all files in leaf folders'
                        'to a single Item named after the folder')
    args = parser.parse_args()

    g = GirderCli(args.username, args.password, bool(args.dryrun),
                  args.blacklist.split(','), host=args.host, port=args.port,
                  apiRoot=args.api_root, scheme=args.scheme,
                  apiUrl=args.api_url, apiKey=args.api_key)
    if args.c == 'upload':
        g.upload(args.local_folder, args.parent_id, args.parent_type,
                 leaf_folders_as_items=args.leaf_folders_as_items,
                 reuse_existing=args.reuse)
    elif args.c == 'download':
        if args.parent_type != 'folder':
            print('download command only accepts parent-type of folder')
        else:
            g.downloadFolderRecursive(args.parent_id, args.local_folder)
    else:
        print('No implementation for command %s' % args.c)


if __name__ == '__main__':
    main()  # pragma: no cover
