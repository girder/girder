Installation Quickstart
=======================

This process will install Girder's prerequisites for a Python 2 environment on common systems.

Basic System Prerequisites
--------------------------

.. tabs::
   .. group-tab:: Ubuntu 16.04

      To install basic system prerequisites, run the command:

      .. code-block:: bash

         sudo apt-get install -y python-pip python-virtualenv

      To install system prerequisites for Girder's ``ldap`` plugin, run the command:

      .. code-block:: bash

         sudo apt-get install -y libldap2-dev libsasl2-dev

   .. group-tab:: Ubuntu 14.04

      To install basic system prerequisites, run the command:

      .. code-block:: bash

         sudo apt-get install -y python-pip python-virtualenv python-dev

      To install system prerequisites for Girder's ``ldap`` plugin, run the command:

      .. code-block:: bash

         sudo apt-get install -y libldap2-dev libsasl2-dev

   .. group-tab:: RHEL (CentOS) 7

      To install basic system prerequisites:

        First, enable the `Extra Packages for Enterprise Linux <https://fedoraproject.org/wiki/EPEL>`_ YUM repository:

        .. code-block:: bash

           sudo yum -y install epel-release

        Then, run the command:

        .. code-block:: bash

           sudo yum -y install python2-pip python-virtualenv gcc python-devel curl

      To install system prerequisites for Girder's ``ldap`` plugin, run the command:

      .. code-block:: bash

         sudo yum -y install openldap-devel cyrus-sasl-devel

   .. group-tab:: macOS

      Install `Homebrew <https://brew.sh/>`_.

      To install all the prerequisites at once just use:

      .. code-block:: bash

         brew install python

      .. note:: OS X ships with Python in ``/usr/bin``, so you might need to change your PATH or explicitly run
                ``/usr/local/bin/python`` when invoking the server so that you use the version with the correct site
                packages installed.

.. _virtualenv-install:

Python Virtual Environment (optional)
-------------------------------------

To create and enable a Python virtual environment, run the commands:

.. code-block:: bash

   virtualenv girder_env
   source girder_env/bin/activate
   pip install -U pip setuptools

.. note:: You will need to re-run

          .. code-block:: bash

             source girder_env/bin/activate

          in any other shell where you want to install or run Girder.

MongoDB
-------

.. tabs::
   .. group-tab:: Ubuntu 16.04

      To install, run the commands:

      .. code-block:: bash

         sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2930ADAE8CAF5059EE73BB4B58712A2291FA4AD5
         echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.6 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.6.list
         sudo apt-get update
         sudo apt-get install -y mongodb-org-server mongodb-org-shell

      MongoDB server will register itself as a systemd service (called ``mongod``). To start it immediately and on every
      reboot, run the commands:

      .. code-block:: bash

         sudo systemctl start mongod
         sudo systemctl enable mongod

   .. group-tab:: Ubuntu 14.04

      To install, run the commands:

      .. code-block:: bash

         sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2930ADAE8CAF5059EE73BB4B58712A2291FA4AD5
         echo "deb [ arch=amd64 ] https://repo.mongodb.org/apt/ubuntu trusty/mongodb-org/3.6 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.6.list
         sudo apt-get update
         sudo apt-get install -y mongodb-org-server mongodb-org-shell

      MongoDB server will register itself as an Upstart service (called ``mongod``), and will automatically start
      immediately and on every reboot.

   .. group-tab:: RHEL (CentOS) 7

      To install, create a file at ``/etc/yum.repos.d/mongodb-org-3.6.repo``, with:

      .. code-block:: cfg

         [mongodb-org-3.6]
         name=MongoDB Repository
         baseurl=https://repo.mongodb.org/yum/redhat/$releasever/mongodb-org/3.6/x86_64/
         gpgcheck=1
         enabled=1
         gpgkey=https://www.mongodb.org/static/pgp/server-3.6.asc

      then run the command:

      .. code-block:: bash

         sudo yum -y install mongodb-org-server mongodb-org-shell

      MongoDB server will register itself as a systemd service (called ``mongod``), and will automatically start on
      every reboot. To start it immediately, run the command:

      .. code-block:: bash

         sudo systemctl start mongod

   .. group-tab:: macOS

      To install, run the command:

      .. code-block:: bash

         brew install mongodb

      MongoDB does not run automatically as a service on macOS, so you'll need to either configure it as a service
      yourself, or just ensure it's running manually via the following command:

      .. code-block:: bash

        mongod -f /usr/local/etc/mongod.conf

.. _nodejs-install:

Node.js
-------
Node.js v8.0 is the `active LTS release <https://github.com/nodejs/Release#release-schedule>`_, though later versions
can also be used instead.

.. tabs::
   .. group-tab:: Ubuntu 16.04

      To install, run the commands:

      .. code-block:: bash

         curl -sL https://deb.nodesource.com/setup_8.x | sudo -E bash -
         sudo apt-get install -y nodejs

   .. group-tab:: Ubuntu 14.04

      To install, run the commands:

      .. code-block:: bash

         curl -sL https://deb.nodesource.com/setup_8.x | sudo -E bash -
         sudo apt-get install -y nodejs

   .. group-tab:: RHEL (CentOS) 7

      To install, run the commands:

      .. code-block:: bash

         curl --silent --location https://rpm.nodesource.com/setup_8.x | sudo bash -
         sudo yum -y install nodejs

   .. group-tab:: macOS

      To install, run the command:

      .. code-block:: bash

         brew install node

Girder
------

Proceed to the :doc:`installation <installation>` guide to install Girder itself.
