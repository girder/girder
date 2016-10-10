System Prerequisites
====================

The following software packages are required to be installed on your system:

* `Python 2.7 or 3.4 <https://www.python.org>`_
* `pip <https://pypi.python.org/pypi/pi>`_
* `MongoDB 2.6+ <http://www.mongodb.org/>`_
* `Node.js <http://nodejs.org/>`_
* `curl <http://curl.haxx.se/>`_
* `zlib <http://www.zlib.net/>`_
* `libjpeg <http://libjpeg.sourceforge.net/>`_

Additionally, in order to send out emails to users, Girder will need to be able
to communicate with an SMTP server. Proper installation and configuration of
an SMTP server on your system is beyond the scope of these docs, but we
recommend setting up `Postfix <http://www.postfix.org/documentation.html>`_.

See the specific instructions for your platform below.

.. note:: We perform continuous integration testing using Python 2.7 and Python 3.4.
   The system *should* work on other versions of Python 3 as well, but we do not
   verify that support in our automated testing at this time, so use at your own
   risk.

.. warning:: Some Girder plugins do not support Python 3 at this time due to
   third party library dependencies. Namely, the HDFS Assetstore plugin and the
   Metadata Extractor plugin will only be available in a Python 2.7 environment.

* :ref:`debian-ubuntu`
* :ref:`centos-fedora-rhel`
* :ref:`archlinux`
* :ref:`os-x`
* :ref:`windows`

.. _debian-ubuntu:

Debian / Ubuntu
---------------

Install the prerequisites using APT: ::

    sudo apt-get install curl g++ git libffi-dev make python-dev python-pip libjpeg-dev zlib1g-dev

MongoDB 2.6 requires a special incantation to install at this time. Install
the APT key with the following: ::

    sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10

For Debian, create the following configuration file for the MongoDB APT repository: ::

    echo 'deb http://downloads-distro.mongodb.org/repo/debian-sysvinit dist 10gen' \
        | sudo tee /etc/apt/sources.list.d/mongodb.list

For Ubuntu, instead create the following configuration file: ::

    echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' \
        | sudo tee /etc/apt/sources.list.d/mongodb.list

Reload the package database and install MongoDB server using APT: ::

    sudo apt-get update
    sudo apt-get install mongodb-org-server

With Ubuntu 16.04, create a systemd init script at

``/lib/systemd/system/mongod.service``: ::

  [Unit]
  Description=High-performance, schema-free document-oriented database
  After=network.target
  Documentation=https://docs.mongodb.org/manual

  [Service]
  User=mongodb
  Group=mongodb
  ExecStart=/usr/bin/mongod --quiet --config /etc/mongod.conf

  [Install]
  WantedBy=multi-user.target

and start it with: ::

  sudo service mongod start

Enable the Node.js APT repository: ::

    curl -sL https://deb.nodesource.com/setup_4.x | sudo bash -

Install Node.js and NPM using APT: ::

    sudo apt-get install nodejs

.. note:: It's recommended to get the latest version of the npm package manager, and Girder currently
   requires at least version 3 of npm. To upgrade to the latest npm, run: ::

      npm install -g npm

   This may need to be run as root using ``sudo``.

.. _centos-fedora-rhel:

CentOS / Fedora / Red Hat Enterprise Linux
------------------------------------------

For CentOS and Red Hat Enterprise Linux, enable the
`Extra Packages for Enterprise Linux <https://fedoraproject.org/wiki/EPEL>`_
YUM repository: ::

   sudo yum install epel-release

Install the prerequisites using YUM: ::

   sudo yum install curl gcc-c++ git libffi-devel make python-devel python-pip libjpeg-turbo-devel zlib-devel

Create a file ``/etc/yum.repos.d/mongodb.repo`` that contains the following
configuration information for the MongoDB YUM repository:

.. code-block:: cfg

    [mongodb]
    name=MongoDB Repository
    baseurl=http://downloads-distro.mongodb.org/repo/redhat/os/x86_64/
    gpgcheck=0
    enabled=1

Install MongoDB server using YUM: ::

    sudo yum install mongodb-org-server

Enable the Node.js YUM repository: ::

    curl -sL https://rpm.nodesource.com/setup_4.x | sudo bash -

Install Node.js and NPM using YUM: ::

    sudo yum install nodejs

.. _archlinux:

Arch Linux
----------

For Arch Linux it is important to note that Python 3 is default. This means
that most commands will need a 2 appending to them, i.e. python2, pip2, ...

Install the prerequisites using the pacman tool: ::

    sudo pacman -S python2 python2-pip mongodb nodejs

.. _os-x:

OS X
----

It is recommended to use `Homebrew <http://brew.sh/>`_ to install the required
packages on OS X.

To install all the prerequisites at once just use: ::

    brew install python mongodb node

.. note:: OS X ships with Python in ``/usr/bin``, so you might need to change your
   PATH or explicitly run ``/usr/local/bin/python`` when invoking the server so
   that you use the version with the correct site packages installed.

.. _windows:

Windows
-------

.. warning:: **Windows is not supported or tested. This information is
   provided for developers. Use at your own risk.**

Download, install, and configure MongoDB server following the
`instructions <http://docs.mongodb.org/manual/tutorial/install-mongodb-on-windows/>`_
on the MongoDB website, and download and run the Node.js
`Windows Installer <http://nodejs.org/download/>`_ from the Node.js website.

Download and install the `Windows MSI Installer <https://www.python.org/downloads/windows/>`_
for the latest Python 2 release from the Python website, and then  download and
run the `ez_setup.py <https://bootstrap.pypa.io/ez_setup.py>`_ bootstrap script
to install `Setuptools <https://pypi.python.org/pypi/setuptools>`_ for Python.
You may need to add ``python\scripts`` to your path for NPM to work as expected.

From a command prompt, install pip: ::

    easy_install pip

If bcrypt fails to install using pip (e.g., with Windows 7 x64 and Python
2.7), you need to manually install it prior to installing girder. You can
build the package from source or download a wheel file from
`<https://bitbucket.org/alexandrul/py-bcrypt/downloads>`_ and install it
with the following: ::

    pip install wheel
    pip install py_bcrypt.whl
