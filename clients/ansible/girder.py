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


def class_spec(cls, include=None):
    include = include if include is not None else []

    for fn, method in getmembers(cls, predicate=ismethod):
        if fn in include:
            spec = getargspec(method)
            # spec.args[1:] so we don't include 'self'
            params = spec.args[1:]
            d = len(spec.defaults) if spec.defaults is not None else 0
            r = len(params) - d

            yield (fn, {"required": params[:r],
                        "optional": params[r:]})


class GirderClientModule(GirderClient):

    # Exclude these methods from both 'raw' mode
    _include_methods = ['get']

    _debug = True

    def exit(self):
        if not self._debug:
            del self.message['debug']

        self.module.exit_json(changed=self.changed, **self.message)

    def __init__(self):
        self.changed = False
        self.message = {"msg": "Success!", "debug": {}}

        self.spec = dict(class_spec(self.__class__,
                                    GirderClientModule._include_methods))
        self.required_one_of = self.spec.keys()



    def __call__(self, module):
        self.module = module

        super(GirderClientModule, self).__init__(
            **{p: self.module.params[p] for p in
               ['host', 'port', 'apiRoot',
                'scheme', 'dryrun', 'blacklist']
               if module.params[p] is not None})

        try:
            self.authenticate(
                username=self.module.params['username'],
                password=self.module.params['password'])

            self.message['debug']['token'] = self.token

        except AuthenticationError:
            self.module.fail_json(msg="Could not Authenticate!")

        for method in self.required_one_of:
            if self.module.params[method] is not None:
                self.__process(method)
                self.exit()

        self.fail_json(msg="Could not find executable method!")

    def __process(self, method):
        params = {}
        args = self.module.params[method]

        for param in self.spec[method]['required']:
            if param not in args.keys():
                self.module.fail_json(
                    msg="{} is required for {}".format(param, method))
            params[param] = args[param]

        for param in self.spec[method]['optional']:
            if param in args.keys():
                params[param] = args[param]

        ret = getattr(self, method)(**params)

        self.message['gc_return'] = ret


    def createUser(self):
        self.message['debug']['msg'] = "Successfully got to createUser!"
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
    }

    gcm = GirderClientModule()

    for method in gcm.required_one_of:
        argument_spec[method] = dict(type='dict')

    module = AnsibleModule(
        argument_spec       = argument_spec,
        required_one_of     = [gcm.required_one_of],
        mutually_exclusive  = gcm.required_one_of,
        supports_check_mode = False)

    if not HAS_GIRDER_CLIENT:
        module.fail_json(msg="Could not import GirderClient!")

    try:
        gcm(module)

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
