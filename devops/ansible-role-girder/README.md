girder.girder
=============
[![Apache 2.0](https://img.shields.io/badge/license-Apache%202-blue.svg)](https://raw.githubusercontent.com/girder/ansible-role-girder/master/LICENSE)
[![Build Status](https://travis-ci.org/girder/ansible-role-girder.svg?branch=master)](https://travis-ci.org/girder/ansible-role-girder)

An Ansible role to install [Girder](https://github.com/girder/girder).

Further documentation on provisioning can be found [here](https://girder.readthedocs.io/en/latest/provisioning.html).

Requirements
------------

Ubuntu 16.04+.

Role Variables
--------------

| parameter             | required | default | comments                                                       |
| --------------------- | -------- | ------- | ---------------------------------------------------------------|
| girder_virtualenv     | yes      | none    | Path to a Python virtual environment to install Girder in.     |
| girder_version        | no       |         | PyPI version of Girder to install.                             |
| girder_web            | no       | yes     | Whether to build the Girder web client.                        |
| girder_daemonize      | no       | no      | Whether to install the systemd service.                        |
| girder_pip_extra_args | no       |         | Any extra arguments to pass to ``pip`` when installing Girder. |
| girder_package        | no       | girder  | Package name to install via ``pip``, can be a path.            |
