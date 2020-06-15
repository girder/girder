Installation
============

This tutorial will install a production-ready Girder on Ubuntu 18.04.

Prerequisites
-------------
Before running this, you must provide:

* A "server": an (ideally fresh) Ubuntu 18.04 system, with:

  * A ``sudo``-capable user.
  * Inbound access from the internet on TCP port 80 and 443.
  * Outbound access to the internet on UDP port 53. Many firewalls (e.g. the
    `AWS EC2 default security group <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-network-security.html#default-security-group>`_)
    do not allow this by default.
  * A DNS entry, so its public IP address is resolvable from the internet.

* A "controller": a machine with
  `Ansible installed <https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html>`_
  and SSH access to the server.

* An "assetstore" for storing uploaded files on Girder. This may be either:

  * A location on the server's filesystem (which may be mounted external storage).
  * An AWS S3 bucket.

* Credentials for an outbound SMTP server, ideally with STARTTLS or TLS.

* An email address for the administrator of the system.

Install Girder With Ansible
---------------------------
Download Template Files
+++++++++++++++++++++++
Download the following files to a fresh directory on the controller machine:

* `requirements.yml <https://raw.githubusercontent.com/girder/girder/master/devops/production-template/requirements.yml>`_
* `hosts.yml <https://raw.githubusercontent.com/girder/girder/master/devops/production-template/hosts.yml>`_
* `playbook.yml <https://raw.githubusercontent.com/girder/girder/master/devops/production-template/playbook.yml>`_
* `provision.sh <https://raw.githubusercontent.com/girder/girder/master/devops/production-template/provision.sh>`_

Make ``provision.sh`` executable:

.. code-block:: bash

   chmod +x ./provision.sh

Configure Inventory
+++++++++++++++++++
Edit ``hosts.yml``, in accordance with the inline comments.
This will configure Ansible to find and login to the server.

Configure The Playbook
++++++++++++++++++++++
Edit ``playbook.yml``, in accordance with the inline comments.
This will configure necessary details of the provisioning process.

.. note::
   Spoof ``nginx_registration_email`` at your own risk.
   The email address is only provided to Let's Encrypt,
   `to provide warnings in case HTTPS auto-renewal is failing <https://letsencrypt.org/docs/expiration-emails/>`_.
   Under normal circumstances, no emails should ever be sent.

.. note::
   When specifying Girder plugins, PyPI package names of published Girder plugin packages should be
   used whenever possible. See :ref:`Plugins <plugins>` for a list of official Girder plugins and associated
   PyPI package names.

   Unpublished plugin packages may be specified in accordance with
   `pip's VCS support <https://pip.pypa.io/en/stable/reference/pip_install/#vcs-support>`_.

Run The Playbook
++++++++++++++++
Run the ``provision.sh`` script, which will download external role files and run the playbook:

.. code-block:: bash

   ./provision.sh

If the server user requires a password to use sudo, you may be prompted for a "become" password.
Enter the password of the server user at this point.

When the script completes, Girder should be fully installed! There is no need for additional setup
via SSH.

Initial Setup
-------------
Admin Console
+++++++++++++

The first user to be created in the system is automatically given admin permission
over the instance, so the first thing you should do after starting your instance for
the first time is to register a user. After that succeeds, you should see a link
appear in the navigation bar that says ``Admin console``.

TODO: SMTP

Plugins
+++++++
To change settings for plugins, click the ``Admin console`` navigation link, then click
``Plugins``. Here, you will see a list of installed plugins. If the plugin has
settings, click on the associated gear icon to modify them.

For information about specific plugins, see the :ref:`Plugins <plugins>` section.

Create Assetstore
+++++++++++++++++
After you have enabled any desired plugins and restarted the server, the next
recommended action is to create an ``Assetstore`` for your system. No users
can upload data to the system until an assetstore is created, since all files
in Girder must reside within an assetstore. See the :ref:`Assetstores <assetstores>` section
for a brief overview of ``Assetstores``.
