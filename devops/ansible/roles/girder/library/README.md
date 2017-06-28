Girder Ansible Client
=====================

Use ansible to configure a running girder instance. Currently this supports configuring users plugins and assetstores. Additionally the module supports non-idempotent ```get```, ```put```, ```post```, and ```delete``` API requests.  You can install this module by copying ```girder.py``` out of the girder source tree and placing it in a ```library/``` folder alongside your top level playbooks. You may also modify the ```ANSIBLE_LIBRARY``` environment variable,  or pass a custom ```--module-path``` to ansible-playbook to provide access to the library.  For more information see [Developing Modules](http://docs.ansible.com/ansible/developing_modules.html) in the ansible documentation.

### Important Note:
The girder ansible module relies on the girder-client to do most of the heavy lifting.  You must ensure that girder-client is installed in your environment before attempting to use the girder module. For most use cases this means simply installing the girder-client utility before using the girder module.

```yaml
- name: install girder-client pip package
  pip: name=girder-client version=1.1.3
  sudo: yes

  # Code that uses girder module

```

### Example using 'user'

```yaml
# Ensure "admin" user exists
- name: Create 'admin' User
  girder:
    user:
      firstName: "John"
      lastName: "Doe"
      login: "admin"
      password: "letmein"
      email: "john.doe@test.com"
      admin: yes
    state: present
```
#### Ensure a 'foobar' user exists

```yaml
- name: Create 'foobar' User
  girder:
    username: "admin"
    password: "letmein"
    user:
      firstName: "Foo"
      lastName: "Bar"
      login: "foobar"
      password: "foobarbaz"
      email: "foo.bar@test.com"
      admin: yes
    state: present
```
#### Remove the 'foobar' user
```yaml
- name: Remove 'foobar' User
  username: "admin"
  password: "letmein"
  girder:
    user:
      login: "foobar"
      password: "foobarbaz"
    state: absent

```


### Example using 'plugins'
To enable or disable all plugins you may pass the "*" argument.  This does not (yet) support arbitrary regexes.

```yaml

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

- name: Ensure jobs and gravatar plugins are enabled
  girder:
    username: "admin"
    password: "letmein"
    plugins:
      - jobs
      - gravatar
    state: present
```
**Note:** that the list of enabled plugins is now ```thumbnails```, ```jobs```, ```gravatar```. The 'plugins' task ensures that plugins are enabled or disabled, it does *not* define the complete list of enabled or disabled plugins. Additionally,  while the plugins are enabled they will not be active until the server is restarted. This should be achieved through another task (either through setting up girder as a system level task,  or through posting to system/restart).


### Filesystem Assetstore Tests

```yaml
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
```
**Note:** Currently only filesystem assetstore types are supported.

### Examples using get

```yaml
# Get my info
- name: Get users from http://localhost:80/api/v1/users
  girder:
    username: 'admin'
    password: 'letmein'
    get:
      path: "users"
  register: ret_val
```
Prints debugging messages with the emails of the users from the last task by accessing ```gc_return``` of the registered variable ```ret_val```


```yaml
- name: print emails of users
  debug: msg="{{ item['email'] }}"
  with_items: "{{ ret_val['gc_return'] }}"
```


### Advanced usage
Supports get, post, put, delete methods,  but does not guarantee idempotence on these methods!

```yaml
- name: Restart the server
  girder:
    username: "admin"
    password: "letmein"
    put:
      path: "system/restart"
```

An example of posting an item to Girder Note that this is NOT idempotent. Running multiple times will create "An Item", "An Item (1)", "An Item (2)", etc..


#### Show use of 'token' for making subsequent authentication requests

```yaml
- name: Get Me
  girder:
    username: "admin"
    password: "letmein"
    get:
      path: "user/me"
  register: ret

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
```
