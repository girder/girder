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
    from girder_client import GirderClient, AuthenticationError, HttpError
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
   - This module implements two different modes,  'do'  and 'raw.' The raw
     mode makes direct pass throughs to the girder client and does not attempt
     to be idempotent,  the 'do' mode implements methods that strive to be
     idempotent.  This is designed to give the developer the most amount of
     flexability possible.
options:

'''

EXAMPLES = '''
# Comment about example
- action: girder opt1=arg1 opt2=arg2
'''


def class_spec(cls, exclude=None):
    exclude = exclude if exclude is None else []

    for fn, method in getmembers(cls, predicate=ismethod):

        # Note, change to _exclude_methods
        if not fn.startswith("_") and fn not in exclude:

            spec = getargspec(getattr(cls, fn))
            # spec.args[1:] so we don't include 'self'
            params = spec.args[1:]
            d = len(spec.defaults) if spec.defaults is not None else 0
            r = len(params) - d

            yield (fn, {"required": params[:r],
                        "optional": params[r:]})


class GirderClientModule(object):

    # Exclude these methods from both 'raw' mode
    _exclude_gc_methods = ['authenticate',
                           'add_folder_upload_callback',
                           'add_item_upload_callback']

    # Exclude these methods from 'do' mode
    _exclude_local_methods = ['exit']

    _debug = True

    def exit(self):
        if not self._debug:
            del self.message['debug']

        self.module.exit_json(changed=self.changed, **self.message)

    # See: https://github.com/ansible/ansible/commit/31609e1b
    def _check_required_if(self, spec):
        if spec is None:
            return
        for (key, val, requirements) in spec:
            missing = []
            if key in self.module.params and self.module.params[key] == val:
                for check in requirements:
                    count = self.module._count_terms(check)
                    if count == 0:
                        missing.append(check)

                if len(missing) > 0:
                    message = "{} is {} but the following are missing: {}"
                    self.module.fail_json(msg=message.format(key, val, ','.join(missing)))


    def __init__(self, module, required_if):
        self.module = module
        self.changed = False
        self.message = {"msg": "Success!",
                        "debug": {}}

        self._check_required_if(spec)

        self.gc = GirderClient(**{p: self.module.params[p] for p in
                                  ['host', 'port', 'apiRoot',
                                   'scheme', 'dryrun', 'blacklist']
                                  if module.params[p] is not None})
        try:
            self.gc.authenticate(
                username=self.module.params['username'],
                password=self.module.params['password'])

            self.message['debug']['token'] = self.gc.token

        except AuthenticationError as e:
            self.module.fail_json(msg="Could not Authenticate!")

        if 'raw' in self.module.params:
            self._process_raw()
        else:
            self._process_do()

        self.exit()

    def __process(self, obj, mode, exclude):
        spec = dict(class_spec(obj.__class__, exclude))
        func = self.module.params[mode]
        params = {}

        for param in spec[func]['required']:
            params[param] = self.module.params[param]

        for param in spec[func]['optional']:
            if param in self.module.params:
                params[param] = self.module.params[param]

        ret = getattr(obj, func)(**params)

        # TODO: How do we actually set facts/register return variables?
        self.message['debug']['return_value'] = ret

    def _process_raw(self):
        self.__process(self.gc, 'raw', self._exclude_gc_methods)

    def _process_do(self):
        self.__process(self, 'do', self._exclude_local_methods)

    def createUser(self):
        self.message['debug']['msg'] = "Successfully got to createuser"
        pass


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
        'scheme': dict(default=None),
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

    argument_spec['raw'] = dict(choices=[])
    argument_spec['do'] = dict(choices=[])
    # argument_spec['func'] = dict( required=False, choices = [])

    required_if = []
    for method, args in class_spec(GirderClient,
                                   GirderClientModule._exclude_gc_methods):
        argument_spec['raw']['choices'].append(method)
        required_if.append(("raw", method, args['required']))



    module = AnsibleModule(
        argument_spec       = argument_spec,
        mutually_exclusive  = [["raw", "do"]],
        require_one_of      = (['raw', 'do']),
        supports_check_mode = False)

    if not HAS_GIRDER_CLIENT:
        module.fail_json(msg="Could not import GirderClient!")

    try:
        # Note: required_if should be moved into AnsibleModule once
        # https://github.com/ansible/ansible/commit/31609e1b is available
        # in a released version of Ansible.
        GirderClientModule(module, required_if)

    except HttpError as e:
        import traceback
        module.fail_json(msg="{}:{}\n{}\n{}".format(e.__class__, str(e),
                                                    e.responseText,
                                                    traceback.format_exc()))
    except Exception as e:
        import traceback
        # exc_type, exc_obj, exec_tb = sys.exc_info()
        module.fail_json(msg="{}: {}\n\n{}".format(e.__class__,
                                                   str(e),
                                                   traceback.format_exc()))


if __name__ == '__main__':
    main()
