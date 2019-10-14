.. _provisioning:

Provisioning
============
Girder can be automatically be provisioned using the popular IT automation tool Ansible.

See the published Ansible roles:

* `girder.girder <https://galaxy.ansible.com/girder/girder>`_
* `girder.mongodb <https://galaxy.ansible.com/girder/mongodb>`_
* `girder.nginx <https://galaxy.ansible.com/girder/nginx>`_

Using Ansible to configure a running Girder instance
####################################################
The Girder role also provides a fully fledged Ansible module to configure Girder in a declarative manner.

For details on usage, see the documentation on the Girder Ansible module.

FAQ
###
How do I control the user that Girder runs under?
-------------------------------------------------
The Ansible playbook assumes that the user being used to provision the machine is the user which
Girder will run as. This greatly simplifies the role logic and reduces problematic behavior with
privilege deescalation in Ansible.

See http://docs.ansible.com/ansible/become.html#becoming-an-unprivileged-user for more information.
