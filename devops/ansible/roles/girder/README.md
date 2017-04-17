girder.girder
=============
[![Apache 2.0](https://img.shields.io/badge/license-Apache%202-blue.svg)](https://raw.githubusercontent.com/girder/ansible-role-girder/master/LICENSE)
[![Build Status](https://travis-ci.org/girder/ansible-role-girder.svg?branch=master)](https://travis-ci.org/girder/ansible-role-girder)

An Ansible role to install [Girder](https://github.com/girder/girder).

Further documentation on provisioning can be found [here](https://girder.readthedocs.io/en/latest/provisioning.html).

Requirements
------------

Ubuntu 14.04/16.04 or CentOS 7.

Role Variables
--------------

| parameter                  | required | default      | comments                                                                                                                                                            |
| -------------------------- | -------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| girder_path                | no       | $HOME/girder | Path to download and build Girder in.                                                                                                                               |
| girder_version             | no       | master       | Git commit-ish for fetching Girder.                                                                                                                                 |
| girder_virtualenv          | no       | none         | Path to a Python virtual environment to install Girder in.                                                                                                          |
| girder_clone               | no       | yes          | Whether provisioning should clone Girder into `girder_path`.                                                                                                        |
| girder_update              | no       | yes          | Whether provisioning should fetch new versions via git.                                                                                                             |
| girder_force               | no       | yes          | Whether provisioning should discard modified files in the working directory.                                                                                        |
| girder_web                 | no       | yes          | Whether to build the Girder web client.                                                                                                                             |
| girder_always_build_assets | no       | no           | Whether to always rebuild client side assets (has no effect if girder_web is disabled).                                                                             |
| girder_daemonize           | no       | yes          | Whether to install the relevant service files (systemd or upstart). Disabling this can be useful inside of containers which might not have an init system.          |
| girder_enabled             | no       | yes          | Whether to enable the installed service (requires `girder_daemonize`).                                                                                              |
| girder_web_extra_args      | no       | none         | Any additional arguments to pass to `girder-install web`. Passing `--all-plugins` can be useful if your environment doesn't have access to Mongo at provision time. |

Generated Facts
---------------

| fact name                 | comments                                                                                                                                                |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| girder_files_updated      | Whether or not the files installed for Girder changed during provisioning. This can be useful for determining if client side assets need to be rebuilt. |
| girder_use_upstart        | Whether Girder decided to use upstart as the init system.                                                                                               |
| girder_use_systemd        | Whether Girder decided to use systemd as the init system.                                                                                               |
| girder_install_executable | The full path to the `girder-install` executable.                                                                                                       |

Examples
--------
Examples can be found [here](https://github.com/girder/girder/tree/master/devops/ansible/examples).
