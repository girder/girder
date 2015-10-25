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
    _include_methods = ['get', 'put', 'post', 'delete',
                        'plugins']

    _debug = True

    def exit(self):
        if not self._debug:
            del self.message['debug']

        self.module.exit_json(changed=self.changed, **self.message)

    def fail(self, msg):
        self.module.fail_json(msg)

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
            self.fail("Could not Authenticate!")

        for method in self.required_one_of:
            if self.module.params[method] is not None:
                self.__process(method)
                self.exit()

        self.fail("Could not find executable method!")

    def __process(self, method):
        # Paramaters from the YAML file
        params = self.module.params[method]
        # Final list of arguments to the function
        args = []
        # Final list of keyword arguments to the function
        kwargs = {}

        if type(params) is dict:
            for arg_name in self.spec[method]['required']:
                if arg_name not in params.keys():
                    self.fail("{} is required for {}".format(arg_name, method))
                args.append(params[arg_name])

            for kwarg_name in self.spec[method]['optional']:
                if kwarg_name in params.keys():
                    kwargs[kwarg_name] = args[kwarg_name]

        elif type(params) is list:
            args = params
        else:
            args = [params]

        ret = getattr(self, method)(*args, **kwargs)

        self.message['debug']['method'] = method
        self.message['debug']['args'] = args
        self.message['debug']['kwargs'] = kwargs
        self.message['debug']['params'] = params

        self.message['gc_return'] = ret


    def plugins(self, *plugins):
        import json
        ret = []

        available_plugins = self.get("system/plugins")
        self.message['debug']['available_plugins'] = available_plugins

        plugins = set(plugins)
        enabled_plugins = set(available_plugins['enabled'])


        # Could maybe be expanded to handle all regular expressions?
        if "*" in plugins:
            plugins = set(available_plugins['all'].keys())

        # Fail if plugins are passed in that are not available
        if not plugins <= set(available_plugins["all"].keys()):
            self.fail("{}, not available!".format(
                ",".join(list(plugins - available_plugins))
            ))

        # If we're trying to ensure plugins are present
        if self.module.params['state'] == 'present':
            # If plugins is not a subset of enabled plugins:
            if not plugins <= enabled_plugins:
                # Put the union of enabled_plugins nad plugins
                ret = self.put("system/plugins",
                               {"plugins":
                                json.dumps(list(plugins | enabled_plugins))})
                self.changed = True

        # If we're trying to ensure plugins are absent
        elif self.module.params['state'] == 'absent':
            # If there are plugins in the list that are enabled
            if len(enabled_plugins & plugins):

                # Put the difference of enabled_plugins and plugins
                ret = self.put("system/plugins",
                               {"plugins":
                                json.dumps(list(enabled_plugins - plugins))})
                self.changed = True

        return ret


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
        'state': dict(default="present", choices=['present', 'absent'])
    }

    gcm = GirderClientModule()

    for method in gcm.required_one_of:
        argument_spec[method] = dict()

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
