Installation
============

Before you install, see the :doc:`installation quickstart <installation-quickstart>` guide to make sure you have all
required system dependencies installed.

Activate the virtual environment
--------------------------------

If you're :ref:`using a virtual environment <virtualenv-install>` for Girder (which is recommended), remember to
activate it with:

.. code-block:: bash

   source girder_env/bin/activate

Replace ``girder_env`` with the path to your virtual environment, as appropriate.

Sources
-------

Girder can be installed either from the `Python Package Index (pypi) <https://pypi.python.org/pypi>`_
or via a `Git <https://git-scm.com/>`_ repository.
Installing from pypi gives you the latest distributed version. Installing from git would be
more suitable for development or to have a specific commit, or to use the latest Girder
features before they are released in official packages.

Install from PyPI
+++++++++++++++++

To install the Girder distribution from the Python package index, simply run ::

    pip install girder

This will install the core Girder server as a site package in your system
or virtual environment. At this point, you might want to check the
:doc:`configuration <configuration>` to change your plugin and logging
paths.  In order to use the web interface, you must also install the web client
libraries. Girder installs a Python script that will automatically build and
install these libraries for you. Just run the following command: ::

   girder build

.. note:: Installing the web client code requires Node.js. See the :ref:`Node.js installation guide <nodejs-install>`
          for installation instructions.

.. note:: If you installed Girder into your system ``site-packages``, you may
   need to run the above commands as root.

Once this is done, you are ready to start using Girder as described in this
section: :ref:`run-girder`.

Install from Git repository
+++++++++++++++++++++++++++

If you wish to develop Girder itself, or need to switch to an unreleased branch, you can install Girder via git.
Obtain the Girder source code by cloning the Git repository on

`GitHub <https://github.com>`_: ::

    git clone https://github.com/girder/girder.git
    pip install -e ./girder

Plugins must be installed as separate packages. Once all plugins are installed,
you can build the web client code by running: ::

    girder build


.. _run-girder:

Run
---

To run Girder, just use the following command: ::

    girder serve

Then, open http://localhost:8080/ in your web browser, and you should see the application.

Initial Setup
-------------

Admin Console
+++++++++++++

The first user to be created in the system is automatically given admin permission
over the instance, so the first thing you should do after starting your instance for
the first time is to register a user. After that succeeds, you should see a link
appear in the navigation bar that says ``Admin console``.

Enable Plugins
++++++++++++++

The next recommended action is to enable any plugins you want to run on your server.
Click the ``Admin console`` navigation link, then click ``Plugins``. Here, you
can turn plugins on or off. Whenever you change the set of plugins that are
enabled, you need to press the **Restart** button at the top of the
Plugins page to restart the server and apply the change.

For information about specific plugins, see the :ref:`Plugins <plugins>` section.

Create Assetstore
+++++++++++++++++

After you have enabled any desired plugins and restarted the server, the next
recommended action is to create an ``Assetstore`` for your system. No users
can upload data to the system until an assetstore is created, since all files
in Girder must reside within an assetstore. See the :ref:`Assetstores <assetstores>` section
for a brief overview of ``Assetstores``.

Installing third-party plugins
------------------------------

Third party plugins are packaged as standalone python packages.  To install one,
install the package and rebuild the web client. ::

   pip install <plugin name>
   girder build
