.. _provisioning:

Provisioning
============
Girder is packaged for provisioning through the popular IT automation tool Ansible.

Specifically, Girder is available as an Ansible role to be fetched through Ansible Galaxy.
This allows for a user to point their own Ansible playbook at a number of servers and deploy
Girder with a single command. Provided in Girder are a number of example playbooks to demonstrate
various ways Girder can be deployed using Ansible.

To test these roles, one can use Vagrant with any of our playbooks to deploy Girder to a live machine.

.. note:: Our playbooks are only currently supporting Ubuntu 14.04 and CentOS 7, and require Ansible >= 2.1.1.

Example: Deploying Girder with NGINX to a VirtualBox
####################################################
Assuming a working copy of Girder is in your current directory: ::

   GIRDER_EXAMPLE=girder-nginx vagrant up

.. note:: A full list of examples that can be used exist in devops/ansible/examples.

After a few minutes of running you should have a functioning Girder instance sitting behind an NGINX
proxy at http://localhost:9080.

Additionally, our examples support running on a CentOS 7 virtual machine. The above example can be executed on such a machine by running the following command: ::

  GIRDER_EXAMPLE=girder-nginx VAGRANT_BOX=centos/7 vagrant up

.. note:: The `centos/7` box requires guest additions in order to work with shared folders. This means you may need the `vagrant-vbguest` plugin.

Using Ansible outside of Vagrant
################################
Our Vagrantfile configures Ansible to make the process seamless, but there are a few differences when
using Ansible outside of the context of a Vagrant machine.

Namely, the role that Vagrant uses is referred to by the folder name "girder" because you happen to have a working copy of Girder checked out, but this isn't required. By specifying the namespaced Ansible Galaxy version of Girder in your playbook and requirements file, the role will be fetched automatically.

Using Ansible to configure a running Girder instance
####################################################
The Girder role also provides a fully fledged Ansible client to configure Girder in a declarative manner.

For details on usage, see the documentation on the Girder Ansible client.

.. seealso::

   The girder-configure-lib example demonstrates usage of the Girder Ansible client.

FAQ
###
How do I control the user that Girder runs under?
-------------------------------------------------
The Ansible playbook assumes that the user being used to provision the machine is the user which
Girder will run as. This greatly simplifies the role logic and reduces problematic behavior with
privilege deescalation in Ansible.

See http://docs.ansible.com/ansible/become.html#becoming-an-unprivileged-user for more information.
