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

# Ansible's module magic requires this to be
# 'from ansible.module_utils.basic import *' otherwise it will error out. See:
# https://github.com/ansible/ansible/blob/v1.9.4-1/lib/ansible/module_common.py#L41-L59
# For more information on this magic. For now we noqa to prevent flake8 errors
from ansible.module_utils.basic import *  # noqa


DOCUMENTATION = '''
---
module: girder_plugin_dir
author: "Chris Kotfila (chris.kotfila@kitware.com)
version_added: "0.1"
short_description: A module that configures the girder plugin directory
requirements: [ girder ]
'''

EXAMPLES = '''


'''

try:
    import os
    import ConfigParser as cp

    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False


class GirderPluginDirModule(object):

    _debug = True

    def exit(self, msg=None):
        if not self._debug:
            del self.message['debug']

        if msg is not None:
            self.message['msg'] = msg

        self.module.exit_json(changed=self.changed, **self.message)

    def fail(self, msg):
        self.module.fail_json(msg=msg)

    def __init__(self, module):
        self.module = module
        self.changed = False
        self.message = {"msg": "Success!", "debug": {
            "module_args": module.params
        }}

        dist_path = os.path.join(self.module.params['girder_dir'],
                                 'girder', 'conf', 'girder.dist.cfg')
        local_path = os.path.join(self.module.params['girder_dir'],
                                  'girder', 'conf', 'girder.local.cfg')

        self.message['debug']['dist_path'] = dist_path
        self.message['debug']['local_path'] = local_path

        self.config = cp.ConfigParser()
        # Read in config file
        if not os.path.exists(local_path):
            try:
                self.message['debug']['src'] = dist_path
                self.config.read(dist_path)
            except IOError:
                self.fail("Could not read {}!".format(dist_path))
        else:
            try:
                self.message['debug']['src'] = local_path
                self.config.read(local_path)
            except IOError:
                self.fail("Could not read {}!".format(local_path))

        # Add/Remove plugin
        if self.module.params['state'] == 'present':
            self.add_plugin_dir(self.module.params['plugin_dir'])
        elif self.module.params['state'] == 'absent':
            self.remove_plugin_dir(self.module.params['plugin_dir'])

        # Write out config file
        if self.changed:
            with open(local_path, "wb") as fh:
                self.config.write(fh)

        self.exit()

    def add_plugin_dir(self, path):
        # If single string, convert to list
        if isinstance(path, basestring):
            path = set([path])
        else:
            path = set(path)

        girder_plugin_dir = set([os.path.join(self.module.params['girder_dir'],
                                              "plugins")])

        self.message['debug']['path'] = list(path)
        # Add the section if it doesn't alraedy exist
        if not self.config.has_section('plugins'):
            self.config.add_section('plugins')

        try:
            plugin_dirs = set(self.config.get("plugins",
                                              "plugin_directory").split(":"))

            # Remove girder_plugin_dir if it exists
            plugin_dirs = plugin_dirs - girder_plugin_dir

            # If path is not a subset of plugin_dirs we
            # are about to affect a change.
            self.changed = not set(path) <= set(plugin_dirs)
        except cp.NoOptionError:
            plugin_dirs = set([])
            self.changed = True

        if self.changed:
            plugin_dirs |= path
            # Add girder_plugin_dir back in at the front of the list
            plugin_dirs = list(girder_plugin_dir) + list(plugin_dirs)

            self.config.set("plugins", "plugin_directory",
                            ":".join(plugin_dirs))

        return

    def remove_plugin_dir(self, path):
        if not self.config.has_section('plugins'):
            return

        girder_plugin_dir = set([os.path.join(self.module.params['girder_dir'],
                                              "plugins")])

        # If single string, convert to list
        if isinstance(path, basestring):
            path = set([path])
        else:
            path = set(path)

        self.message['debug']['path'] = list(path)

        try:
            plugin_dirs = set(self.config.get("plugins",
                                              "plugin_directory").split(":"))

            # Remove girder_plugin_dir if it exists
            plugin_dirs = plugin_dirs - girder_plugin_dir

            # If there are common path between plugin_dirs and path
            # We are about to affect a change
            self.changed = bool(len(plugin_dirs & path))

            if self.changed:
                # We've only got the girder_plugin directory left in
                # plugin_directory

                leftover = plugin_dirs - path

                if len(leftover) == 0:
                    # If all we've got left is the girder plugin dirctory
                    self.config.remove_option("plugins", "plugin_directory")
                    # If that was it in the plugins section,  remove that too
                    if len(self.config.items("plugins")) == 0:
                        self.config.remove_section("plugins")
                else:
                    # Add girder_plugin_dir back in at the front of the list
                    plugin_dirs = list(girder_plugin_dir) + list(leftover)

                    self.config.set("plugins", "plugin_directory",
                                    ":".join(plugin_dirs))

            return

        except cp.NoOptionError:
            return


def main():
    """Entry point for ansible girder plugin directory module

    :returns: Nothing
    :rtype: NoneType

    """

    module = AnsibleModule(
        argument_spec={
            'girder_dir': dict(required=True),
            'plugin_dir': dict(required=True),
            'state': dict(default="present", choices=['present', 'absent'])})

    if IMPORT_SUCCESS is False:
        module.fail_json(msg="Unable to import required libraries!")

    try:
        GirderPluginDirModule(module)

    except Exception as e:
        import traceback
        # exc_type, exc_obj, exec_tb = sys.exc_info()
        module.fail_json(msg="{}: {}\n\n{}".format(e.__class__,
                                                   str(e),
                                                   traceback.format_exc()))


if __name__ == '__main__':
    main()
