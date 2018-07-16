girder.girder
=============
[![Apache 2.0](https://img.shields.io/badge/license-Apache%202-blue.svg)](https://raw.githubusercontent.com/girder/ansible-role-girder/master/LICENSE)
[![Build Status](https://travis-ci.org/girder/ansible-role-girder.svg?branch=master)](https://travis-ci.org/girder/ansible-role-girder)

An Ansible role to install [Girder](https://github.com/girder/girder).

Further documentation on provisioning can be found [here](https://girder.readthedocs.io/en/latest/provisioning.html).

Requirements
------------

Ubuntu 14.04/16.04 or CentOS 7.

Installing against a custom python or in a virtualenv:

This role always installs in a virtualenv against the ansible_python_interpreter unless girder_virtualenv is specified and pre-created.

This role requires virtualenv already be installed.


Role Variables
--------------

| parameter                  | required | default        | comments                                                                                                                                                            |
| -------------------------- | -------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| girder_path                | no       | $HOME/girder                         | Path to download and build Girder in.                                                                                                                               |
| girder_repo                | no       | https://github.com/girder/girder.git | Git origin for fetching Girder.                                                                                                                                     |
| girder_version             | no       | master                               | Git commit-ish for fetching Girder.                                                                                                                                 |
| girder_virtualenv          | no       | none                                 | Path to a Python virtual environment to install Girder in.                                                                                                          |
| girder_clone               | no       | yes                                  | Whether provisioning should clone Girder into `girder_path`.                                                                                                        |
| girder_update              | no       | yes                                  | Whether provisioning should fetch new versions via git.                                                                                                             |
| girder_force               | no       | yes                                  | Whether provisioning should discard modified files in the working directory.                                                                                        |
| girder_web                 | no       | yes                                  | Whether to build the Girder web client.                                                                                                                             |
| girder_daemonize           | no       | yes                                  | Whether to install the relevant service files (systemd or upstart). Disabling this can be useful inside of containers which might not have an init system.          |
| girder_enabled             | no       | yes                                  | Whether to enable the installed service (requires `girder_daemonize`).                                                                                              |
| girder_plugins             | no       | []                                   | List of paths to external plugins to install.                                                                                                                       |
| girder_web_extra_args      | no       | none                                 | Any additional arguments to pass to `girder-install web`. Passing `--all-plugins` can be useful if your environment doesn't have access to Mongo at provision time. |
| girder_user                | no       | $SSH_USER                            | The (already existing) user to run Girder under, this defaults to `ansible_user_id` which is typically the user Ansible is running under.                           |

Examples
--------
Examples can be found [here](https://github.com/girder/girder/tree/master/devops/ansible/examples).
