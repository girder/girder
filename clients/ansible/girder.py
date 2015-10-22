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
import inspect

try:
    from girder_client import GirderClient, AuthenticationError
    HAS_GIRDER_CLIENT = True
except ImportError:
    HAS_GIRDER_CLIENT = False

DOCUMENTATION= '''
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

def func_args(func):
    """Return the arguments of a function as a string

    Do not return the argument 'self' on class methods

    :param func: a function or method
    :returns: A list of strings,  each string is an argument to func
    :rtype: list

    """
    return [k for k in func.__code__.co_varnames if k != 'self']

class GirderClientModule(GirderClient):


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

def main():
    """Entry point for ansible girder client module

    :returns: Nothing
    :rtype: NoneType

    """
    argument_spec = {
        k: dict(default=None) for k in func_args(GirderClient.__init__)
    }

    argument_spec['username'] = dict(required=True)
    argument_spec['password'] = dict(required=True)

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
