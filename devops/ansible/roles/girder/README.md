girder.girder
=============
[![Apache 2.0](https://img.shields.io/badge/license-Apache%202-blue.svg)](https://raw.githubusercontent.com/girder/ansible-role-girder/master/LICENSE)
[![Build Status](https://travis-ci.org/girder/ansible-role-girder.svg?branch=master)](https://travis-ci.org/girder/ansible-role-girder)

An Ansible role to install [Girder](https://github.com/girder/girder).

Requirements
------------

This is intended to be run on a clean Ubuntu 14.04 system.

Role Variables
--------------

The following variables may be overridden:

* `girder_path`: Path to download and build Girder in.
* `girder_version`: Git commit-ish for fetching Girder.
* `girder_virtualenv`: Path to a Python virtual environment to install Girder in.
* `girder_update`: Whether provisioning should fetch new versions via git.
* `girder_force`: Whether provisioning should discard modified files in the working directory.
* `girder_web`: Whether to build the Girder web client.

Dependencies
------------

This role depends on the following roles from Ansible Galaxy:

* `Stouts.mongodb`

These will be automatically fetched if your requirements.yml file contains:
```
---

- src: girder.girder
```

Examples
--------
Examples can be found [here](https://github.com/girder/girder/tree/ansible-role-refactor/devops/ansible/examples).
