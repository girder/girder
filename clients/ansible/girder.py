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
   - Manage a girder instance using the RESTful API
options:
    host:
        required: false
        default: 'localhost'
        description:
            - domain or IP of the host running girder
    port:
        required: false
        default: '80' for http, '443' for https
        description:
            - port the girder instance is running on

    apiRoot:
        required: false
        default: '/api/v1'
        description:
            - path on server corresponding to the root of Girder REST API

    scheme:
        required: false
        default: 'http'
        description:
            - A string containing the scheme for the Girder host

    dryrun:
        required: false
        default: None (passed through)
        description:
            - See GirderClient.__init__()

    blacklist:
        required: false
        default: None (passed through)
        description:
            - See GirderClient.__init__()

    username:
        required: true
        description:
            - Valid username for the system
            - Required with password
            - must be specified if 'token' is not specified
                - (See note on 'user')

    password:
        required: true
        description:
            - Valid password for the system
            - Required with username
            - must be specified if 'token' is not specified
                - (See note on 'user')
    token:
        required: true
        description:
            - A girder client token
            - Can be retrieved by accessing the accessing the 'token' attribute
              from a successfully authenticated call to girder in a previous task.
            - Required if 'username' and 'password' are not specified
                - (See note on 'user')
    state:
        required: false
        default: "present"
        choices: ["present", "absent"]
        description:
            - Used to indicate the presence or absence of a resource
              - e.g.,  user, plugin, assetstore

    user:
        required: false
        description:
            - If using the 'user' task, you are NOT REQUIRED to pass in a
              'username' & 'password',  or a 'token' attributes. This is because
              the first user created on an fresh install of girder is automatically
              made an administrative user. Once you are certain you have an admin
              user you should use those credentials in all subsequent tasks that use
              the 'user' task.

            - Takes a mapping of key value pairs
              options:
                  login:
                      required: true
                      description:
                          - The login name of the user
                  password:
                      required: true
                      description:
                          - The password of the user

                  firstName:
                      required: false
                      default: pass through to girder client
                      description:
                          - The first name of the user

                  lastName:
                      required: false
                      default: pass through to girder client
                      description:
                          - The last name of the user
                  email:
                      required: false
                      default: pass through to girder client
                      description:
                          - The email of the user
                  admin:
                      required: false
                      default: false
                      description:
                          - If true,  make the user an administrator.


    plugin:
        required: false
        description:
            - Specify what plugins should be activated (state: present)
              or deactivated (state: absent).
            - Takes a list of plugin names,  incorrect names are silently
              ignored

    assetstore:
        required: false
        description:
            - Specifies an assetstore
            - Takes many options depending on 'type'
              options:
                  name:
                      required: true
                      description:
                          - Name of the assetstore
                  type:
                      required: true
                      choices: ['filesystem', 'gridfs', 's3', 'hdfs']
                      description:
                          - Currently only 'filesystem' has been tested
                  readOnly:
                      required: false
                      default: false
                      description:
                          - Should the assetstore be read only?
                  current:
                      required: false
                      default: false
                      description:
                          - Should the assetstore be set as the current assetstore?

              options (filesystem):
                  root:
                      required: true
                      description:
                          -  Filesystem path to the assetstore

              options (gridfs) (EXPERIMENTAL):
                   db:
                       required: true
                       description:
                           - database name
                   mongohost:
                       required: true
                       description:
                           - Mongo host URI

                   replicaset:
                       required: false
                       default: ''
                       description:
                           - Replica set name

              options (s3) (EXPERIMENTAL):
                   bucket:
                       required: true
                       description:
                           - The S3 bucket to store data in

                   prefix:
                       required: true
                       description:
                           - Optional path prefix within the bucket under which files will be stored

                   accessKeyId:
                       required: true
                       description:
                           - the AWS access key ID to use for authentication

                   secret:
                       required: true
                       description:
                           - the AWS secret key to use for authentication

                   service:
                       required: false
                       default: s3.amazonaws.com
                       description:
                           - The S3 service host (for S3 type)
                           - This can be used to specify a protocol and port
                             -  use the form [http[s]://](host domain)[:(port)]
                           - Do not include the bucket name here

              options (hdfs) (EXPERIMENTAL):
                   host:
                       required: true
                       description:
                           - None
                   port:
                       required: true
                       description:
                           - None
                   path:
                       required: true
                       description:
                           - None
                   user:
                       required: true
                       description:
                           - None
                   webHdfsPort
                       required: true
                       description:
                           - None

'''

EXAMPLES = '''


#############
# Example using 'user'
###


# Ensure "admin" user exists
- name: Create 'admin' User
  girder:
    user:
      firstName: "Chris"
      lastName: "Kotfila"
      login: "admin"
      password: "letmein"
      email: "chris.kotfila@kitware.com"
      admin: yes
    state: present

# Ensure a 'foobar' user exists
- name: Create 'foobar' User
  girder:
    username: "admin"
    password: "letmein"
    user:
      firstName: "Foo"
      lastName: "Bar"
      login: "foobar"
      password: "foobarbaz"
      email: "foo.bar@kitware.com"
      admin: yes
    state: present

# Remove the 'foobar' user
- name: Remove 'foobar' User
  username: "admin"
  password: "letmein"
  girder:
    user:
      login: "foobar"
      password: "foobarbaz"
    state: absent


#############
# Example using 'plugins'
###

# To enable or disable all plugins you may pass the "*"
# argument.  This does not (yet) support arbitrary regexes
- name: Disable all plugins
  girder:
    username: "admin"
    password: "letmein"
    plugins: "*"
    state: absent

- name: Enable thumbnails plugin
  girder:
    username: "admin"
    password: "letmein"
    port: 8080
    plugins:
      - thumbnails
    state: present

# Note that 'thumbnails'  is still enabled from the previous task,
# the 'plugins' task ensures that plugins are enabled or disabled,
# it does NOT define the complete list of enabled or disabled plugins.
- name: Ensure jobs and gravatar plugins are enabled
  girder:
    username: "admin"
    password: "letmein"
    plugins:
      - jobs
      - gravatar
    state: present



############
# Filesystem Assetstore Tests
#

- name: Create filesystem assetstore
  girder:
    username: "admin"
     password: "letmein"
     assetstore:
       name: "Temp Filesystem Assetstore"
       type: "filesystem"
       root: "/data/"
       current: true
     state: present

- name: Delete filesystem assetstore
  girder:
    username: "admin"
    password: "letmein"
    assetstore:
      name: "Temp Filesystem Assetstore"
      type: "filesystem"
      root: "/tmp/"
    state: absent

############
# Examples using get
#


# Get my info
- name: Get users from http://localhost:80/api/v1/users
  girder:
    username: 'admin'
    password: 'letmein'
    get:
      path: "users"
    register: ret_val

# Prints debugging messages with the emails of the users
# From the last task by accessing 'gc_return' of the registered
# variable 'ret_val'
- name: print emails of users
  debug: msg="{{ item['email'] }}"
  with_items: "{{ ret_val['gc_return'] }}"


#############
# Advanced usage
#

# Supports get, post, put, delete methods,  but does
# not guarantee idempotence on these methods!

- name: Restart the server
  girder:
    username: "admin"
    password: "letmein"
    put:
      path: "system/restart"

# An example of posting an item to Girder
# Note that this is NOT idempotent. Running
# multiple times will create "An Item", "An Item (1)",
# "An Item (2)", etc..

- name: Get Me
  girder:
    username: "admin"
    password: "letmein"
    get:
      path: "user/me"
  register: ret

# Show use of 'token' for subsequent authentication
- name: Get my public folder
  girder:
    token: "{{ ret['token'] }}"
    get:
      path: "folder"
      parameters:
        parentType: "user"
        parentId: "{{ ret['gc_return']['_id'] }}"
        text: "Public"
  register: ret


- name: Post an item to my public folder
  girder:
    host: "data.kitware.com"
    scheme: 'https'
    token: "{{ ret['token'] }}"
    post:
      path: "item"
      parameters:
        folderId: "{{ ret['gc_return'][0]['_id'] }}"
        name: "An Item"


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
                        'plugins', 'user', 'assetstore']

    _debug = True

    def exit(self):
        if not self._debug:
            del self.message['debug']

        self.module.exit_json(changed=self.changed, **self.message)

    def fail(self, msg):
        self.module.fail_json(msg=msg)

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
        # If a username and password are set
        if self.module.params['username'] is not None:
            try:
                self.authenticate(
                    username=self.module.params['username'],
                    password=self.module.params['password'])

            except AuthenticationError:
                self.fail("Could not Authenticate!")

        # If a token is set
        elif self.module.params['token'] is not None:
            self.token = self.module.params['token']

        # Else error if we're not trying to create a user
        elif self.module.params['user'] is None:
            self.fail("Must pass in either username & password, "
                      "or a valid girder_client token")

        self.message['token'] = self.token

        for method in self.required_one_of:
            if self.module.params[method] is not None:
                self.__process(method)
                self.exit()

        self.fail("Could not find executable method!")

    def __process(self, method):
        # Parameters from the YAML file
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
                    kwargs[kwarg_name] = params[kwarg_name]

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

    def user(self, login, password, firstName=None,
             lastName=None, email=None, admin=False):

        if self.module.params['state'] == 'present':

            # Fail if we don't have firstName, lastName and email
            for var_name, var in [('firstName', firstName),
                                  ('lastName', lastName), ('email', email)]:
                if var is None:
                    self.fail("{} must be set if state "
                              "is 'present'".format(var_name))

            try:
                ret = self.authenticate(username=login,
                                        password=password)

                me = self.get("user/me")

                # List of fields that can actually be updated
                updateable = ['firstName', 'lastName', 'email', 'admin']
                passed_in = [firstName, lastName, email, admin]

                # If there is actually an update to be made
                if set([(k, v) for k, v in me.items() if k in updateable]) ^ \
                   set(zip(updateable, passed_in)):

                    self.put("user/{}".format(me['_id']),
                             parameters={
                                 "login": login,
                                 "firstName": firstName,
                                 "lastName": lastName,
                                 "password": password,
                                 "email": email,
                                 "admin": "true" if admin else "false"
                             })
                    self.changed = True
            # User does not exist (with this login info)
            except AuthenticationError:
                ret = self.post("user", parameters={
                    "login": login,
                    "firstName": firstName,
                    "lastName": lastName,
                    "password": password,
                    "email": email,
                    "admin": "true" if admin else "false"
                })
                self.changed = True

        elif self.module.params['state'] == 'absent':
            ret = []
            try:
                ret = self.authenticate(username=login,
                                        password=password)

                me = self.get("user/me")

                self.delete('user/{}'.format(me['_id']))
                self.changed = True
            # User does not exist (with this login info)
            except AuthenticationError:
                ret = []

        return ret

    assetstore_types = {
        "filesystem": 0,
        "girdfs": 1,
        "s3": 2,
        "hdfs": "hdfs"
    }

    def __validate_hdfs_assetstore(self, *args, **kwargs):
        # Check if hdfs plugin is available,  enable it if it isn't
        pass

    def assetstore(self, name, type, root=None, db=None, mongohost=None,
                   replicaset='', bucket=None, prefix='', accessKeyId=None,
                   secret=None, service='s3.amazonaws.com', host=None,
                   port=None, path=None, user=None, webHdfsPort=None,
                   readOnly=False, current=False):

            # Fail if somehow we have an asset type not in assetstore_types
        if type not in self.assetstore_types.keys():
            self.fail("assetstore type {} is not implemented!".format(type))

        argument_hash = {
            "filesystem": {'name': name,
                           'type': self.assetstore_types[type],
                           'root': root},
            "gridfs": {'name': name,
                       'type': self.assetstore_types[type],
                       'db': db,
                       'mongohost': mongohost,
                       'replicaset': replicaset},
            "s3": {'name': name,
                   'type': self.assetstore_types[type],
                   'bucket': bucket,
                   'prefix': prefix,
                   'accessKeyId': accessKeyId,
                   'secret': secret,
                   'service': service},
            'hdfs': {'name': name,
                     'type': self.assetstore_types[type],
                     'host': host,
                     'port': port,
                     'path': path,
                     'user': user,
                     'webHdfsPort': webHdfsPort}
        }

        # Fail if we don't have all the required attributes
        # for this asset type
        for k, v in argument_hash[type].items():
            if v is None:
                self.fail("assetstores of type "
                          "{} require attribute {}".format(type, k))

        # Set optional arguments in the hash
        argument_hash[type]['readOnly'] = readOnly
        argument_hash[type]['current'] = current

        ret = []
        # Get the current assetstores
        assetstores = {a['name']: a for a in self.get("assetstore")}

        self.message['debug']['assetstores'] = assetstores

        # If we want the assetstore to be present
        if self.module.params['state'] == 'present':

            # And the asset store exists
            if name in assetstores.keys():

                id = assetstores[name]['_id']

                ####
                # Fields that could potentially be updated
                #
                # This is necessary because there are fields in the assetstores
                # that do not hash (e.g., capacity) and fields in the
                # argument_hash that are not returned by 'GET' assetstore (e.g.
                # readOnly). We could be more precise about this
                # (e.g., by only checking items that are relevant to this type)
                # but readability suffers.
                updateable = ["root", "mongohost", "replicaset", "bucket",
                              "prefix", "db", "accessKeyId", "secret",
                              "service", "host", "port", "path", "user",
                              "webHdfsPort", "current"]

                # tuples of (key,  value) for fields that can be updated
                # in the assetstore
                assetstore_items = set((k, assetstores[name][k])
                                       for k in updateable
                                       if k in assetstores[name].keys())

                # tuples of (key,  value) for fields that can be updated
                # in the argument_hash for this assetstore type
                arg_hash_items = set((k, argument_hash[type][k])
                                     for k in updateable
                                     if k in argument_hash[type].keys())

                # if arg_hash_items not a proper subset of assetstore_items
                if not arg_hash_items <= assetstore_items:
                    # Update
                    ret = self.put("assetstore/{}".format(id),
                                   parameters=argument_hash[type])

                    self.changed = True

            # And the asset store does not exist
            else:
                try:
                    # If __validate_[type]_assetstore exists then call the
                    # function with argument_hash. E.g.,  to check if the
                    # HDFS plugin is enabled
                    getattr(self, "__validate_{}_assetstore"
                            .format(type))(**arguments_hash)
                except AttributeError:
                    pass

                ret = self.post("assetstore",
                                parameters=argument_hash[type])
                self.changed = True
        # If we want the assetstore to be gone
        elif self.module.params['state'] == 'absent':
            # And the assetstore exists
            if name in assetstores.keys():
                id = assetstores[name]['_id']
                ret = self.delete("assetstore/{}".format(id),
                                  parameters=argument_hash[type])

        return ret






def main():
    """Entry point for ansible girder client module

    :returns: Nothing
    :rtype: NoneType

    """

    # Default spec for initalizing and authenticating
    argument_spec = {
        # __init__
        'host': dict(),
        'port': dict(),
        'apiRoot': dict(),
        'scheme': dict(),
        'dryrun': dict(),
        'blacklist': dict(),

        # authenticate
        'username': dict(),
        'password': dict(),
        'token':    dict(),

        # General
        'state': dict(default="present", choices=['present', 'absent'])
    }

    gcm = GirderClientModule()

    for method in gcm.required_one_of:
        argument_spec[method] = dict()

    module = AnsibleModule(
        argument_spec       = argument_spec,
        required_one_of     = [gcm.required_one_of,
                               ["token", "username", "user"]],
        required_together   = [["username", "password"]],
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
