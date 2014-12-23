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
import glob
import os
from girder_client import GirderClient


class GirderCli(GirderClient):
    """
    """

    def __init__(self, username, password, dryrun=False, blacklist=[],
                 host='localhost', port=8080, apiRoot=None):
        GirderClient.__init__(self, host=host, port=port, apiRoot=apiRoot)
        interactive = password is None
        self.authenticate(username, password, interactive=interactive)
        self.dryrun = dryrun
        self.blacklist = blacklist
        self.item_upload_callbacks = []
        self.folder_upload_callbacks = []

    def add_folder_upload_callback(self, callback):
        self.folder_upload_callbacks.append(callback)

    def add_item_upload_callback(self, callback):
        self.item_upload_callbacks.append(callback)

    def _load_or_create_folder(self, local_folder, parent_folder_id):
        child_folders = self.listFolder(parent_folder_id)
        folder_name = os.path.basename(local_folder)
        folder = None
        for child in child_folders:
            if child['name'] == folder_name:
                folder = child
        if folder is None:
            folder = self.createFolder(parent_folder_id, 'folder',
                                         folder_name, description='')
        return folder

    def _has_only_files(self, local_folder):
        """Returns whether a folder has only files. This will be false if the
        folder contains any subdirectories.
        :param local_folder: full path to the local folder
        """
        return not any(os.path.isdir(os.path.join(local_folder, entry))
                       for entry in os.listdir(local_folder))

    def _create_or_reuse_item(self, local_file, parent_folder_id,
                              reuse_existing=False):
        """Create an item from the local_file in the parent_folder
        :param local_file: full path to a file on the local file system
        :param parent_folder_id: id of parent folder in Girder
        :param reuse_existing: boolean indicating whether to accept an existing
        item
        of the same name in the same location, or create a new one instead
        """
        local_item_name = os.path.basename(local_file)
        item = None
        if reuse_existing:
            children = self.listItem(parent_folder_id, local_item_name)
            for child in children:
                if child['name'] == local_item_name:
                    item = child
                    break

        if item is None:
            item = self.createItem(parent_folder_id, local_item_name,
                                     description='')

        return item

    def _upload_file_to_item(self, local_file, parent_item_id, file_path):
        self.uploadFileToItem(parent_item_id, file_path)

    def _upload_as_item(self, local_file, parent_folder_id, file_path,
                        reuse_existing=False):
        """Function for doing an upload of a file as an item.
        :param local_file: name of local file to upload
        :param parent_folder_id: id of parent folder in Girder
        :param file_path: full path to the file
        :param reuse_existing: boolean indicating whether to accept an existing
        item
        of the same name in the same location, or create a new one instead
        """
        print 'Uploading Item from %s' % local_file
        if not self.dryrun:
            current_item = self._create_or_reuse_item(
                local_file, parent_folder_id, reuse_existing)
            self._upload_file_to_item(
                local_file, current_item['_id'], file_path)

            for callback in self.item_upload_callbacks:
                callback(current_item, file_path)

    def _upload_folder_as_item(self, local_folder, parent_folder_id,
                           reuse_existing=False):
        """Take a folder and use its base name as the name of a new item. Then,
        upload its containing files into the new item as bitstreams.
        :param local_folder: The path to the folder to be uploaded.
        :param parent_folder_id: The id of the destination folder for the new item.
        :param reuse_existing: boolean indicating whether to accept an existing
        item
        of the same name in the same location, or create a new one instead
        """
        print 'Creating Item from folder %s' % local_folder
        if not self.dryrun:
            item = self._create_or_reuse_item(local_folder, parent_folder_id,
                                        reuse_existing)

        subdircontents = sorted(os.listdir(local_folder))
        # for each file in the subdir, add it to the item
        filecount = len(subdircontents)
        for (ind, current_file) in enumerate(subdircontents):
            filepath = os.path.join(local_folder, current_file)
            print 'Adding file %s, (%d of %d) to Item' % (current_file,
                                                          ind + 1, filecount)

            if not self.dryrun:
                self._upload_file_to_item(current_file, item['_id'], filepath)

        if not self.dryrun:
            for callback in self.item_upload_callbacks:
                callback(item, local_folder)

    def _upload_folder_recursive(self, local_folder, parent_folder_id,
                                 leaf_folders_as_items=False,
                                 reuse_existing=False):
        """Function to recursively upload a folder and all of its descendants.
        :param local_folder: full path to local folder to be uploaded
        :param parent_folder_id: id of parent folder in Girder, where new folder
        will be added
        :param leaf_folders_as_items: whether leaf folders should have all files
        uploaded as single items
        :param reuse_existing: boolean indicating whether to accept an existing
        item
        of the same name in the same location, or create a new one instead
        """
        if leaf_folders_as_items and self._has_only_files(local_folder):
            self._upload_folder_as_item(local_folder, parent_folder_id,
                           reuse_existing)
        else:
            filename = os.path.basename(local_folder)
            if filename in self.blacklist:
                if self.dryrun:
                    print "Ignoring file %s as it is blacklisted" % filename
                return

            print 'Creating Folder from %s' % local_folder
            if self.dryrun:
                # create a dryrun placeholder
                folder = {'_id': 'dryrun'}
            else:
                folder = self._load_or_create_folder(
                    local_folder, parent_folder_id)

            for entry in sorted(os.listdir(local_folder)):
                if entry in self.blacklist:
                    if self.dryrun:
                        print "Ignoring file %s as it is blacklisted" % entry
                    continue
                full_entry = os.path.join(local_folder, entry)
                if os.path.islink(full_entry):
                    # os.walk skips symlinks by default
                    print "Skipping file %s as it is a symlink" % entry
                    continue
                elif os.path.isdir(full_entry):
                    self._upload_folder_recursive(
                        full_entry, folder['_id'], leaf_folders_as_items,
                        reuse_existing)
                else:
                    self._upload_as_item(
                        entry, folder['_id'], full_entry, reuse_existing)

    def upload(self, file_pattern, parent_folder_id, parent_type='folder',
               leaf_folders_as_items=False, reuse_existing=False):
        """Upload a pattern of files.

        This will recursively walk down every tree in the file pattern to
        create a hierarchy on the server.  Assumes the parent is a folder.

        :param file_pattern: a glob pattern for files that will be uploaded,
        recursively copying any file folder structures
        :param parent_folder_id: id of the parent folder in girder
        :param leaf_folders_as_items: whether leaf folders should have all files
        uploaded as single items
        :param reuse_existing: boolean indicating whether to accept an existing
        item of the same name in the same location, or create a new one instead
        """
        empty = True
        for current_file in glob.iglob(file_pattern):
            empty = False
            current_file = os.path.normpath(current_file)
            filename = os.path.basename(current_file)
            if filename in self.blacklist:
                if self.dryrun:
                    print "Ignoring file %s as it is blacklisted" % filename
                continue
            if os.path.isfile(current_file):
                self._upload_as_item(
                    os.path.basename(current_file), parent_folder_id,
                    current_file, reuse_existing)
            else:
                self._upload_folder_recursive(
                    current_file, parent_folder_id, leaf_folders_as_items,
                    reuse_existing)
        if empty:
            print 'No matching files: ' + file_pattern

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Perform common Girder CLI operations.')
    parser.add_argument(
        '--reuse', action='store_true',
        help='use existing items of same name at same location or create a new '
        'one')
    parser.add_argument(
        '--blacklist', default='', required=False,
        help='comma separated list of filenames to ignore')
    parser.add_argument(
        '--dryrun', action='store_true',
        help='will not write anything to Girder, only report on what would '
        'happen')
    parser.add_argument('--username', required=False, default=None)
    parser.add_argument('--password', required=False, default=None)
    parser.add_argument('--host', required=False, default='localhost')
    parser.add_argument('--port', required=False, default='8080')
    parser.add_argument('--api-root', required=False, default='/api/v1',
                        help='path to the Girder REST API')
    parser.add_argument('-c', default='upload', choices=['upload'],
                        help='command to run')
    parser.add_argument('folder_id', help='id of Girder target folder')
    parser.add_argument('local_folder', help='path to local target folder')
    parser.add_argument('--leaf-folders-as-items', required=False,
                        action='store_true',
                        help='upload all files in leaf folders'
                        'to a single Item named after the folder')
    args = parser.parse_args()

    g = GirderCli(args.username, args.password, bool(args.dryrun),
                  args.blacklist.split(','), host=args.host, port=args.port,
                  apiRoot=args.api_root)
    if args.c == 'upload':
        g.upload(args.local_folder, args.folder_id,
                 leaf_folders_as_items=args.leaf_folders_as_items,
                 reuse_existing=args.reuse)
    else:
        print 'No implementation for command %s' % args.c
