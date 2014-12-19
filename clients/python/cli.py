import glob
import os
import os.path
import girderclient

class GirderCli(object):
    """
    """

    def __init__(self, username, password, dryrun=False, blacklist=[]):
        self.g = girderclient.GirderClient()
        self.g
        self.g.authenticate(username, password)
        self.dryrun = dryrun
        self.blacklist = blacklist

    def _load_or_create_folder(self, local_folder, parent_folder_id):
        child_folders = self.g.listFolder(parent_folder_id)
        folder_name = os.path.basename(local_folder)
        folder = None
        for child in child_folders:
            if child['name'] == folder_name:
                folder = child
        if folder is None:
            folder = self.g.createFolder(parent_folder_id, 'folder', folder_name, description = '')
        return folder

    def _has_only_files(self, local_folder):
        """Returns whether a folder has only files. This will be false if the
        folder contains any subdirectories.
        :param local_folder: full path to the local folder
        """
        return not any(os.path.isdir(os.path.join(local_folder, entry))
                       for entry in os.listdir(local_folder))

    def _create_or_reuse_item(self, local_file, parent_folder_id, reuse_existing=False):
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
            children = self.g.listItem(parent_folder_id, local_item_name)
            for child in children:
                if child['name'] == local_item_name:
                    item = child
                    break

        if item is None:
            item = self.g.createItem(parent_folder_id, local_item_name, description='')

        return item


    def _upload_file_to_item(self, local_file, parent_item_id, file_path):
        self.g.uploadFileToItem(parent_item_id, file_path)

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
            current_item = self._create_or_reuse_item(local_file, parent_folder_id,
                                                 reuse_existing)
            self._upload_file_to_item(local_file, current_item['_id'], file_path)
        #_create_bitstream(file_path, local_file, current_item_id)
        #for callback in session.item_upload_callbacks:
            #callback(session.communicator, session.token, current_item_id)




    def _upload_folder_recursive(self, local_folder,
                             parent_folder_id,
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
            print 'Creating Item from folder %s' % local_folder
            if not self.dryrun:
                # TODO not implemented
                #_upload_folder_as_item(local_folder, parent_folder_id, reuse_existing)
                pass
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
                folder = self._load_or_create_folder(local_folder, parent_folder_id)

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
                    self._upload_folder_recursive(full_entry,
                                             folder['_id'],
                                             leaf_folders_as_items,
                                             reuse_existing)
                else:
                    self._upload_as_item(entry,
                                    folder['_id'],
                                    full_entry,
                                    reuse_existing)




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
        for current_file in glob.iglob(file_pattern):
            current_file = os.path.normpath(current_file)
            filename = os.path.basename(current_file)
            if filename in self.blacklist:
                if self.dryrun:
                    print "Ignoring file %s as it is blacklisted" % filename
                continue
            if os.path.isfile(current_file):
                self._upload_as_item(os.path.basename(current_file),
                                parent_folder_id,
                                current_file,
                                reuse_existing)
            else:
                self._upload_folder_recursive(current_file,
                                         parent_folder_id,
                                         leaf_folders_as_items,
                                         reuse_existing)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Perform common Girder CLI operations.')
    parser.add_argument('--reuse', action='store_true', help='use existing items of same name at same location or create a new one')
    parser.add_argument('--blacklist', default='', required=False, help='comma separated list of filenames to ignore')
    parser.add_argument('--dryrun', action='store_true', help='will not write anything to Girder, only report on what would happen')
    parser.add_argument('username')
    parser.add_argument('password')
    parser.add_argument('-c', default='upload', choices=['upload'], help='command to run')
    parser.add_argument('folder_id', help='id of Girder target folder')
    parser.add_argument('local_folder', help='path to local target folder')
    args = parser.parse_args()
    g = GirderCli(args.username, args.password, bool(args.dryrun), args.blacklist.split(','))
    if args.c == 'upload':
        g.upload(args.local_folder, args.folder_id, reuse_existing=args.reuse)
    else:
        print 'No implementation for command %s' % args.c
