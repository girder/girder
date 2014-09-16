System Prerequisites
====================

The following software packages are required to be installed on your system:

* `Python 2 <http://python.org>`_
* `pip <https://pypi.python.org/pypi/pi>`_
* `MongoDB 2.6+ <http://www.mongodb.org/>`_
* `node.js <http://nodejs.org/>`_

Additionally, in order to send out emails to users, Girder will need to be able
to communicate with an SMTP server. Proper installation and configuration of
an SMTP server on your system is beyond the scope of these docs, but we
recommend setting up `Postfix <http://www.postfix.org/documentation.html>`_.

See the specific instructions for your platform below.

* :ref:`ubuntu`
* :ref:`rhel-fedora-centos`
* :ref:`mac-osx`
* :ref:`windows`

.. _ubuntu:

Ubuntu
------

Use APT to install the prerequisites on Ubuntu.::

    sudo apt-get install python-pip libffi-dev

Node.js currently isn't in the standard repositories, so run: ::

    sudo apt-get install python-software-properties python g++ make
    sudo add-apt-repository ppa:chris-lea/node.js
    sudo apt-get update
    sudo apt-get install nodejs

MongoDB 2.6 also requires a special incantation to install at this time: ::

    sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
    echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/mongodb.list
    sudo apt-get update
    sudo apt-get install mongodb-org-server

.. _rhel-fedora-centos:

RHEL / Fedora / CentOS
----------------------

TODO

.. _mac-osx:

Mac OSX
-------

It is recommened to use `Homebrew <http://brew.sh/>`_ to install the required
packages on OSX.

To install all of the prerequisites at once just use: ::

    brew install python mongodb node

.. note:: OSX ships with python in /usr/bin, so you might need to change your
   PATH or explicitly run /usr/local/bin/python when invoking the server so
   that you use the version with the correct site packages installed.

.. _windows:

Windows
------

Install setuptools `<https://pypi.python.org/pypi/setuptools>`_ for python.
You may need to add python\scripts to your path (it is necessary for npm to work as expected).

From a command prompt, install pip: ::

    easy_install pip

If bcrypt fails to install using pip (this happened on Windows 7-64 and python 2.7), you need to remove it from the requirements.txt file and manually install it.  You can build it from source or install it from a wheel file from `<https://bitbucket.org/alexandrul/py-bcrypt/downloads>`_.  You can then install the wheel file: ::

    pip install wheel
    pip install py_bcrypt.whl


