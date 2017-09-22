The goal of this Vagrantfile and Ansible setup is to provide a fully
functional single VM with Girder, Girder-Worker, and the item_tasks plugin
so that task developers can focus on their Docker images and not have to
deal with setting up an environment to run their Docker images.  This
should lower the barrier to entry of using the item_tasks system.

Notes
=====

Use with Ansible > v 2.2.0 (tested with v2.2.3).

This will port forward the VM's port ``8080`` (CherryPy/Girder) to the host ``9080``.

The Girder admin user is ``girder`` / ``girder``.

Logs for Girder go to ``/var/log/upstart/girder.log``.
Logs for girder-worker go to ``/var/log/upstart/girder_worker.log``.

Basic operations
================

These commands should be run from the same directory as this ``README`` file,
where the item_tasks ``Vagrantfile`` is located.  If these commands are run
from a different directory, the wrong ``Vagrantfile`` may be used.

Create the box for the first time and provision it
--------------------------------------------------
::

    vagrant up

Provision the box (it should be safe to do this repeatedly)
-----------------------------------------------------------
::

    vagrant provision

Bring up the box after the first time
-------------------------------------
::

    vagrant up

ssh into the box as vagrant/vagrant, with passwordless sudo
-----------------------------------------------------------
::

    vagrant ssh

Halt the box
------------
::

    vagrant halt
