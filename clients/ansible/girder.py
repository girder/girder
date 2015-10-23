#!/usr/bin/python
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

from ansible.module_utils.basic import *
from inspect import getmembers, ismethod, getargspec

try:
    from girder_client import GirderClient, AuthenticationError
    HAS_GIRDER_CLIENT = True
except ImportError:
    HAS_GIRDER_CLIENT = False

DOCUMENTATION = '''
---
module: girder
author: "Chris Kotfila (chris.kotfila@kitware.com)
version_added: "0.1"
short_description: A module that wraps girder_client
requirements: [ girder_client==1.1.0 ]
description:
   - Manage a girder instance useing the RESTful API
options:

'''

EXAMPLES = '''
# Comment about example
- action: girder opt1=arg1 opt2=arg2
'''


class GirderClientModule(GirderClient):

    _exclude_methods = ['authenticate',
                        'add_folder_upload_callback',
                        'add_item_upload_callback']

    def exit(self):
        self.module.exit_json(changed=self.changed, **self.message)

    def __init__(self, module):
        self.module = module
        self.changed = False
        self.message = {"msg": "Success!"}

        super(GirderClientModule, self).__init__(
            **{k: module.params.get(k, None) for k in
               func_args(GirderClient.__init__)})

        try:
            self.authenticate(
                username = module.params.get('username', None),
                password = module.params.get('password', None))

            self.message['token'] = self.token
        except AuthenticationError, e:
            module.fail_json(msg="Could not Authenticate!")



        # call function here

        self.exit()


def class_spec():
    for fn, method in getmembers(GirderClient, predicate=ismethod):

        # Note, change to _exclude_methods
        if not fn.startswith("_") and \
           fn not in GirderClientModule._exclude_methods:

            spec = getargspec(getattr(GirderClient, fn))
            # spec.args[1:] so we don't include 'self'
            params = spec.args[1:]
            d = len(spec.defaults) if spec.defaults is not None else 0
            r = len(params) - d

            yield (fn, {"required": params[:r],
                        "defaults": params[r:]})

def main():
    """Entry point for ansible girder client module

    :returns: Nothing
    :rtype: NoneType

    """

    # Default spec for initalizing and authenticating
    argument_spec = {
        # __init__
        'host': dict(default=None),
        'port': dict(default=None),
        'apiRoot': dict(default=None),
        'dryrun': dict(default=None),
        'blacklist': dict(default=None),

        # authenticate
        'username': dict(required=True),
        'password': dict(required=True),

        # setFolderAccess,  inheritAccessControlRecursive(
        'access': dict(type='dict'),

        # inheritAccessControlRecursive
        'ancestorFolderId': dict(type='str'),

        # sendRestRequest, put
        'data': dict(type='dict'),

        # createItem, createFolder
        'description': dict(type='str'),

        # downloadItem, downloadFolderRecursive
        'dest': dict(type='str'),

        # downloadFile
        'fileId': dict(type='str'),

        # upload
        'file_pattern': dict(type='str'),

        # isFileCurrent
        'filename': dict(type='str'),

        # isFileCurrent, uploadFileToItem
        'filepath': dict(type='str'),

        # post, sendRestRequest
        'files': dict(type='dict'),

        # addMetadataToFolder, downloadFolderRecursive, getFolder,
        # getFolderAccess, listItem, setFolderAcces
        'folderId': dict(type='str'),

        #load_or_create_folder
        'folder_name': dict(type='str'),

        # getResource
        'id': dict(type='str'),

        # addMetadataToItem, downloadItem, getItem, isFileCurrent, uploadFileToIte
        'itemId': dict(type='str'),

        # upload
        'leaf_folders_as_items': dict(type='bool'),

        # addMetadataToFolder, addMetadataToItem
        'metadata': dict(type='dict'),

        # sendRestRequest
        'method': dict(type='str'),

        # createFolder, createItem, downloadItem, listFolder,
        # listItem, load_or_create_item, uploadFile
        'name': dict(type='str'),

        # delete, get, post, put, sendRestRequest
        'parameters': dict(type='dict'),

        # createResource, listResource
        'params': dict(type='dict'),

        # createItem
        'parentFolderId': dict(type='str'),

        # listFolder
        'parentFolderType': dict(default='folder', type='str',
                                 choices=['folder', 'user', 'collection']),

        # createFolder, listFolder, uploadFile
        'parentId': dict(type='str'),

        # createFolder, uploadFile
        # Note: createFolder and uploadFile differ on default for this,
        #       this means ansible task MUST specify
        # Note: 'collection' and 'user' are not appropriate for uploadFile
        #       'item' is not appropriate for createFolder,  it is the user's
        #       responsibility to know this!
        'parentType': dict(type='str', choices=['folder', 'user', 'collection', 'item']),

        # load_or_create_item
        'parent_folder_id': dict(type='str',
                                 choices=['collection', 'folder', 'user']),

        # load_or_create_folder, upload
        'parent_id': dict(type='str'),

        # load_or_create_folder, upload
        'parent_type': dict(type='str',
                            choices=['collection', 'folder', 'user']),

        # createResource, delete, downloadFile, get, getResource,
        # listResource, post, put, sendRestReques
        'path': dict(type='str'),

        # getResrouce
        'property': dict(type='str'),

        # inheritAccessControlRecursive, setFolderAccess
        'public': dict(type='bool'),

        # load_or_create_item, upload
        'reuse_existing': dict(type='bool'),

        # uploadFile
        'size': dict(type='str'),

        # uploadFile
        # TODO: add custom uploadFile function to GirderClientModule
        #       to convert stream into 'file-like' object
        'stream': dict(type='str'),

        # listItem
        'text': dict(type='str')
    }

    argument_spec['func'] = dict( require = True, choices = [])


    required_if = []
    for method, args in class_spec():
        argument_spec['func']['choices'].append(method)
        required_if.append(("func", method, args['required']))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=False
    )


    if not HAS_GIRDER_CLIENT:
        module.fail_json(msg="Could not import GirderClient!")

    try:
        GirderClientModule(module)

    except Exception, e:
        module.fail_json(msg=str(e))

    return

if __name__ == '__main__':
    main()
