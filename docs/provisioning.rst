.. _provisioning:

Provisioning
============
Girder is packaged for provisioning through the popular IT automation tool Ansible.

Specifically, Girder is available as an Ansible role, which allows a user to point
their own Ansible playbook at a number of servers and deploy Girder with a single
command. Provided with the role are `testing playbooks` which can serve as
additional reference documentation.

.. note:: Our playbooks are only currently supporting Ubuntu 16.04 and newer.

Using Ansible to configure a running Girder instance
####################################################
The Girder role also provides a fully fledged Ansible client to configure Girder in a declarative manner.

For details on usage, see the documentation on the Girder Ansible client.

FAQ
###
How do I control the user that Girder runs under?
-------------------------------------------------
The Ansible playbook assumes that the user being used to provision the machine is the user which
Girder will run as. This greatly simplifies the role logic and reduces problematic behavior with
privilege deescalation in Ansible.

See http://docs.ansible.com/ansible/become.html#becoming-an-unprivileged-user for more information.
