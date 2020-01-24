# girder.girder
[![Apache 2.0](https://img.shields.io/badge/license-Apache%202-blue.svg)](https://raw.githubusercontent.com/girder/ansible-role-girder/master/LICENSE)
[![Build Status](https://circleci.com/gh/girder/girder.png?style=shield)](https://circleci.com/gh/girder/girder)

An Ansible role to install [Girder](https://github.com/girder/girder).

## Requirements

Ubuntu 18.04+.

Using Python 3 as
[the target host Python interpreter](https://docs.ansible.com/ansible/latest/reference_appendices/interpreter_discovery.html)
is recommended. Setting `ansible_python_interpreter: auto` will enable this behavior.

## Role Variables

| parameter                 | required | default                                      | comments                                                                                  |
| ------------------------- | -------- | -------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `girder_bind_public`      | no       | `false`                                      | Whether to bind to all network interfaces.                                                |
| `girder_daemonize`        | no       | `true`                                       | Whether to install the systemd service.                                                   |
| `girder_database_uri`     | no       | `mongodb://localhost:27017/girder`           | The Connection String URI for MongoDB.                                                    |
| `girder_development_mode` | no       | `false`                                      | Whether to enable Girder's development mode and disable HTTP reverse proxy configuration. |
| `girder_version`          | no       | `latest`                                     | The version of Girder to install, as either ``latest``, ``release``, or a PyPI version.   |
| `girder_virtualenv`       | no       | `{{ ansible_user_dir }}/.virtualenvs/girder` | Path to a Python virtual environment to install Girder in.                                |
| `girder_web`              | no       | `true`                                       | Whether to build the Girder web client.                                                   |
| `girder_package_path`     | no       |                                              | If set, a filesystem path on the target to install the Girder package from.               |

### Notes on `girder_virtualenv`

When `girder_virtualenv` is not defined by the playbook, it functions as an
output variable. It will be set by this role to the location of a new
virtual environment (using the system Python 3) where Girder is installed.
Subsequent roles, `tasks`, or `post_tasks` can use `girder_virtualenv` to
perform actions (often installing Girder plugins) on this same virtual
environment.

When `girder_virtualenv` is defined by the playbook before this role is run,
this role will install Girder to the virtual environment at
`girder_virtualenv`. If no virtual environment exists at this location, one
will be implicitly created using the system Python 3. This allows Girder to be
installed to a virtual environment with custom specifications. For example,
such virtual environments could be at a particular path on disk or be
pre-created using a specific version of Python.

## Example Playbook

A typical playbook using this role may look like:

```yaml
- name: Deploy Girder
  hosts: all
  vars:
    ansible_python_interpreter: auto
  roles:
    - role: girder.girder
  tasks:
    - name: Install Girder plugins
      pip:
        name:
          - girder-hashsum-download
          - girder-oauth
        virtualenv: "{{ girder_virtualenv }}"
      notify:
        - Build Girder web client
        - Restart Girder
```

A typical
[Ansible Galaxy `requirements.yml` file](https://galaxy.ansible.com/docs/using/installing.html#installing-multiple-roles-from-a-file)
should look like:

```yaml
- src: girder.girder
  version: master
```

## License

[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0.html)
