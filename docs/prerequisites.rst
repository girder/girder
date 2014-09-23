System Prerequisites
====================

The following software packages are required to be installed on your system:

* `Python 2 <https://www.python.org>`_
* `pip <https://pypi.python.org/pypi/pi>`_
* `MongoDB 2.6+ <http://www.mongodb.org/>`_
* `Node.js <http://nodejs.org/>`_

Additionally, in order to send out emails to users, Girder will need to be able
to communicate with an SMTP server. Proper installation and configuration of
an SMTP server on your system is beyond the scope of these docs, but we
recommend setting up `Postfix <http://www.postfix.org/documentation.html>`_.

See the specific instructions for your platform below.

* :ref:`debian-ubuntu`
* :ref:`centos-fedora-rhel`
* :ref:`os-x`
* :ref:`windows`

.. _debian-ubuntu:

Debian / Ubuntu
---------------

Install the prerequisites using APT: ::

    sudo apt-get install curl g++ git libffi-dev make python-dev python-pip

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

Enable the Node.js APT repository: ::

    curl -sL https://deb.nodesource.com/setup | sudo bash -

Install Node.js and NPM using APT: ::

    sudo apt-get install nodejs

.. _centos-fedora-rhel:

CentOS / Fedora / Red Hat Enterprise Linux
------------------------------------------

For CentOS and Red Hat Enterprise Linux, enable the
`Extra Packages for Enterprise Linux <https://fedoraproject.org/wiki/EPEL>`_
YUM repository: ::

   sudo yum install epel-release

Install the prerequisites using YUM: ::

   sudo yum install curl gcc-c++ git libffi-devel make python-devel python-pip

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

    curl -sL https://rpm.nodesource.com/setup | sudo bash -

Install Node.js and NPM using YUM: ::

    sudo yum install nodejs

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

Install `Setuptools <https://pypi.python.org/pypi/setuptools>`_ for Python.
You may need to add ``python\scripts`` to your path for NPM to work as
expected.

From a command prompt, install pip: ::

    easy_install pip

If bcrypt fails to install using pip (e.g., with Windows 7 x64 and Python
2.7), you need to remove the line for bcrypt from the ``requirements.txt``
file and manually install it. You can build the package from source or
download a wheel file from
`<https://bitbucket.org/alexandrul/py-bcrypt/downloads>`_ and install it
with the following: ::

    pip install wheel
    pip install py_bcrypt.whl
