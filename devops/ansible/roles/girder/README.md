girder.girder
=============
[![Apache 2.0](https://img.shields.io/badge/license-Apache%202-blue.svg)](https://raw.githubusercontent.com/girder/ansible-role-girder/master/LICENSE)
[![Build Status](https://travis-ci.org/girder/ansible-role-girder.svg?branch=master)](https://travis-ci.org/girder/ansible-role-girder)

An Ansible role to install [Girder](https://github.com/girder/girder).

Further documentation on provisioning can be found [here](https://girder.readthedocs.io/en/latest/provisioning.html).

Requirements
------------

This is intended to be run on a clean Ubuntu 14.04 or 16.04 system.

Role Variables
--------------

| parameter         | required | default      | comments                                                                     |
| ----------------- | -------- | ------------ | ---------------------------------------------------------------------------- |
| girder_path       | no       | $HOME/girder | Path to download and build Girder in.                                        |
| girder_version    | no       | master       | Git commit-ish for fetching Girder.                                          |
| girder_virtualenv | no       | none         | Path to a Python virtual environment to install Girder in.                   |
| girder_update     | no       | yes          | Whether provisioning should fetch new versions via git.                      |
| girder_force      | no       | yes          | Whether provisioning should discard modified files in the working directory. |
| girder_web        | no       | yes          | Whether to build the Girder web client.                                      |

Examples
--------
Examples can be found [here](https://github.com/girder/girder/tree/master/devops/ansible/examples).
