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

   girder-install web

.. note:: Installing the web client code requires Node.js. See the :ref:`Node.js installation guide <nodejs-install>`
          for installation instructions.

.. note:: If you installed Girder into your system ``site-packages``, you may
   need to run the above commands as root.

Once this is done, you are ready to start using Girder as described in this
section: :ref:`run-girder`.

Installing extra dependencies with pip
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Girder comes bundled with a number of :doc:`plugins` that require extra Python
dependencies in order to use.  By default, none of these dependencies will be
installed; however, you can tell pip to install them using pip's
"`extras`_ " syntax.  Each girder plugin requiring extra Python dependencies
can be specified during the pip install.  For example, installing girder with
support for the `celery_jobs` and `geospatial` plugins can be done like this: ::

   pip install girder[celery_jobs,geospatial]

There is also an extra you can use to install the dependencies for all bundled
plugins supported in the current Python environment called ``plugins``: ::

   pip install girder[plugins]

.. warning:: Not all plugins are available in every Python version and platform.
   Specifying a plugin for in an unsupported environment will raise an error.

.. _extras: https://packaging.python.org/en/latest/installing/#installing-setuptools-extras

Install from Git repository
+++++++++++++++++++++++++++

Obtain the Girder source code by cloning the Git repository on
`GitHub <https://github.com>`_: ::

    git clone --branch 2.x-maintenance https://github.com/girder/girder.git
    cd girder

.. note:: Note, it is strongly recommended that downstream (i.e. for production or to
   support plugin development) users installing from Git track the ``2.x-maintenance`` branch, as
   this branch will always point to the latest version (which is typically pre-release) in the 2.x.x
   series.

To run the server, you must install some external Python package
dependencies: ::

    pip install -e .

or: ::

    pip install -e .[plugins]

to install the plugins as well.

.. note:: This will install the most recent versions of all dependencies.
   You can also try to run ``pip install -r requirements.txt`` to duplicate
   the exact versions used by our CI testing environment; however, this
   can lead to problems if you are installing other libraries in the same
   virtual or system environment.

To build the client-side code project, cd into the root of the repository
and run: ::

    girder-install web

This will run multiple `Grunt <http://gruntjs.com>`_ tasks, to build all of
the Javascript and CSS files needed to run the web client application.

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
enabled, you need to press the **Rebuild and restart** button at the top of the
Plugins page to rebuild the web client and restart the server to apply the change.

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

Girder ships with a :ref:`standard library of plugins <plugins>` that can be
enabled in the admin console, but it's common for Girder installations to require
additional third-party plugins to be installed. If you're using a pip installed
version of Girder, you can simply use the following command: ::

    girder-install plugin /path/to/your/plugin

That command will expose the plugin to Girder and build any web client targets
associated with the plugin. You will still need to enable it in the console and
then restart the Girder server before it will be active.

.. note:: The ``girder-install plugin`` command can also accept a list of plugins
   to be installed. You may need to run it as root if you installed Girder at the
   system level.

For development purposes it is possible to symlink (rather than copy) the plugin
directory. This is accomplished with the ``-s`` or ``--symlink`` flag: ::

     girder-install plugin -s /path/to/your/plugin

Enabled plugins installed with ``-s`` may be edited in place and those changes will
be reflected after a server restart.
