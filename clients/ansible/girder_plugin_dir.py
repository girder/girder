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

    def exit(self):
        if not self._debug:
            del self.message['debug']

        self.module.exit_json(changed=self.changed, **self.message)

    def fail(self, msg):
        self.module.fail_json(msg=msg)

    def __init__(self, module):
        self.module = module
        self.changed = False
        self.message = {"msg": "Success!", "debug": {}}

        dist_path = os.path.join(self.module.params['girder_dir'],
                                 'girder', 'conf', 'girder.dist.cfg')
        local_path = os.path.join(self.module.params['girder_dir'],
                                  'girder', 'conf', 'girder.local.cfg')
        self.config = cp.ConfigParser()
        # Read in config file
        if not os.path.exists(local_path):
            try:
                self.config.read(dist_path)
            except IOError:
                self.fail("Could not read {}!".format(dist_path))
        else:
            try:
                self.config.read(local_path)
            except IOError:
                self.fail("Could not read {}!".format(local_path))

        # Add/Remove plugin directory
        if self.module.params['state'] is 'present':
            self.add_plugin_dir(self.module.params['plugin_dir'])
        elif self.module.params['state'] is 'absent':
            self.remove_plugin_dir(self.module.params['plugin_dir'])

        # Write out config file
        if self.changed:
            with open(local_path, "wb") as fh:
                self.config.write(fh)

        self.exit()

    def add_plugin_dir(self, path):
        # If single string, convert to list
        paths = [path] if path is isinstance(path, basestring) else path

        # Add the section if it doesn't alraedy exist
        if not self.config.has_section('plugins'):
            self.config.add_section('plugins')

        try:
            plugin_dirs = self.config.get("plugin_directory").split(":")
            # If paths is not a subset of plugin_dirs we
            # are about to affect a change.
            self.changed = not set(paths) <= set(plugin_dirs)

        except cp.NoOptionError:
            # Option doesn't exist,  make sure we've got atleast
            # The girder_dir plugin directory before adding more
            plugin_dirs = [os.path.join(self.module.params['girder_dir'],
                                        "plugins")]

            self.changed = True

        if self.changed:
            plugin_dirs = plugin_dirs + list(set(paths) - set(plugin_dirs))

            self.config.set("plugins", ":".join(plugin_dirs))

        return

    def remove_plugin_dir(self, path):
        if not self.config.has_section('plugins'):
            return

        # If single string, convert to list
        paths = [path] if path is isinstance(path, basestring) else path

        try:
            plugin_dirs = self.config.get("plugin_directory").split(":")

            # If there are common paths between plugin_dirs and paths
            # We are about to affect a change
            self.changed = bool(len(set(plugins_dir) & set(paths)))

            if self.changed:
                plugin_dirs = plugin_dirs + list(set(plugin_dirs) - set(paths))

                self.config.set("plugins", ":".join(plugin_dirs))

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
