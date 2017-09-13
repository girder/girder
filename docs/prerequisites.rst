System Prerequisites
====================

Server Install
--------------
Installation of Girder's server has the following system dependencies:

* `Python <https://www.python.org>`_ v2.7 or v3.5+

  * This is necessary to run most of the server software.

  .. warning:: Some Girder plugins do not support Python v3 at this time due to third party library dependencies.
               Namely, the ``hdfs_assetstore`` plugin and the ``metadata_extractor`` plugin will only be available in a
               Python v2.7 environment.

  .. note:: Girder performs continuous integration testing using Python v2.7 and Python v3.5. Girder *should* work on
            newer Python v3.6+ versions as well, but that support is not verified by Girder's auftomated testing at this
            time, so use at your own risk.

* `pip <https://pip.pypa.io/>`_ v8.1+

  * This is necessary to install Python packages.

  * v8.1 is required to install packages via `Python wheels <https://pythonwheels.com/>`_, which significantly reduce
    system dependencies on `manylinux <https://github.com/pypa/manylinux>`_-compatible distributions (which includes
    almost everything except Alpine).

* `setuptools <https://setuptools.readthedocs.io/>`_ v21+

  * This is necessary to install Python packages.

  * v21+ is required to parse Girder's ``setup.py`` file, but the latest version can and should be installed via pip.

* A Python virtual environment (optional)

  * This is necessary to prevent conflicts with Girder's Python dependencies and allow installation as a non-root user.

  * Virtual environments are managed by the `virtualenv package <https://virtualenv.pypa.io/>`_ in Python v2.x and by
    the built-in `venv module <https://docs.python.org/3/library/venv.html>`_ in Python v3.5+.

    .. note:: Developers needing to work on several virtual environments should consider using other packages that help
              manage them such as:

              * `virtualenvwrapper <http://virtualenvwrapper.readthedocs.org/en/latest/index.html>`_

              * `autoenv <https://github.com/kennethreitz/autoenv>`_

              * `pyenv-virtualenv <https://github.com/yyuu/pyenv-virtualenv>`_

              * `pyenv-virtualenvwrapper <https://github.com/yyuu/pyenv-virtualenvwrapper>`_

* A C build environment for Python

  * This is necessary to install the `psutil <https://psutil.readthedocs.io/>`_ Python package (a requirement of
    Girder).

  * At a minimum, the environment must include GCC and the Python development headers.

.. note:: In the past, the `cryptography <https://cryptography.io/>`_ Python package (an indirect requirement of Girder)
          required OpenSSL development headers, but ``cryptography`` is now published as a Python wheel.

          In the past, the `CFFI <https://cffi.readthedocs.io/>`_ Python package (an indirect requirement of Girder)
          required ``libffi`` development headers, but ``CFFI`` is now published as a Python wheel.

Server Plugins Install
----------------------
Some of Girder's plugins require additional system dependencies, if they are installed:

* `OpenLDAP <https://www.openldap.org/>`_ v2.4.11+ development headers (for the ``ldap`` plugin)

  * This is necessary to install the `python-ldap <https://www.python-ldap.org/>`_ Python package (a requirement of the
    ``ldap`` plugin).

* `Cyrus SASL <https://www.cyrusimap.org/sasl/>`_ development headers (for the ``ldap`` plugin)

  * This is an optional dependency for installing the `python-ldap <https://www.python-ldap.org/>`_ Python package (a
    requirement of the ``ldap`` plugin).

.. note:: In the past, the `Pillow <https://pillow.readthedocs.io/>`_ Python package (a requirement of the
          ``thumbnails`` plugin ) required ``libjpeg`` and ``zlib`` development headers, but Pillow is now published as
          a Python wheel.

Server Runtime
--------------
Running Girder's server has the following additional system dependencies:

* `MongoDB <https://www.mongodb.org/>`_ v3.2+

  * This is necessary for Girder's primary application database.

  * MongoDB does not need to be installed on the same machine as Girder's server, so long as a network connection to a
    remote MongoDB is possible.

* An SMTP relay (optional)

  * This is necessary to send emails to users and administrators.

  * There are multiple web-based services that provide SMTP relays at no cost for smaller volumes of mail.

    * `Mailgun <https://www.mailgun.com/>`_ is known to work well for typical deployments.

    * `Amazon SES <https://aws.amazon.com/ses/>`_ may be simpler to manage for deployments already in AWS.

    * Any other SMTP service should be compatible, though some may only accept mail from a limited set of "From"
      addresses (which may be configured via a setting within Girder).

  * Advanced system administrators may wish to run their own SMTP server, like
    `Postfix <http://www.postfix.org/documentation.html>`_, as a relay.

    * Beware that self-hosted SMTP relays may need additional configuration with IP whitelisting, SPF, DKIM, and other
      measures before their mail can be reliability delivered to some email providers.

Web Client Build
----------------
Building Girder's web client has the following system dependencies:

* `Node.js <https://nodejs.org/>`_ v8+

  * This is necessary to execute many aspects of the web client build system.

* `npm <https://www.npmjs.com/>`_ v5.2+

  * This is necessary to install web client packages.

* `curl <https://curl.haxx.se/>`_

  * This is necessary to download Fontello files as part of the web client build process.

* `Git <https://git-scm.com/>`_

  * This is necessary to introspect Girder's install environment and generate version information as part of the web
    client build process.

Quick Setup Guide
=================

This process will install Girder's prerequisites for a Python 2 environment on common systems.

Basic System Prerequisites
--------------------------

.. tabs::
   .. group-tab:: Ubuntu 16.04

      To install basic system prerequisites, run the command:

      .. code-block:: bash

         sudo apt-get install -y python-pip python-virtualenv git

      To install system prerequisites for Girder's ``ldap`` plugin, run the command:

      .. code-block:: bash

         sudo apt-get install -y libldap2-dev libsasl2-dev

   .. group-tab:: Ubuntu 14.04

      To install basic system prerequisites, run the command:

      .. code-block:: bash

         sudo apt-get install -y python-pip python-virtualenv python-dev git

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

           sudo yum -y install python2-pip python-virtualenv gcc python-devel curl git

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
   source girder-env/bin/activate
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

npm (optional)
--------------
Node.js v8.x will install npm v5.6 by default, but developers may wish to install the latest npm instead.

To upgrade to the latest npm on all platforms, either:

- `Fix npm's global permissions <https://docs.npmjs.com/getting-started/fixing-npm-permissions>`_,
  then run the command :

  .. code-block:: bash

     npm install -g npm

- Or just run the command:

  .. code-block:: bash

     sudo npm install -g npm

Girder
------

Proceed to the :doc:`installation <installation>` guide to install Girder itself.
