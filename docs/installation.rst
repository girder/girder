Installation
============

Before you install, see the :doc:`prerequisites` guide to make sure you
have all required system packages installed.

Creating a virtual environment
------------------------------

While not strictly required, it is recommended to install Girder within
its own `virtual environment <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_
to isolate its dependencies from other python packages.  To generate a new
virtual environment, first install/update the ``virtualenv`` and ``pip``
packages ::

   sudo pip install -U virtualenv pip

Now create a virtual environment using the
`virtualenv command <http://virtualenv.readthedocs.org/en/latest/userguide.html>`_.
You can place the virtual environment directory wherever you want, but it should
not be moved.  The following command will generate a new directory called
``girder_env`` in your home directory: ::

   virtualenv ~/girder_env

Now you can run ``source ~/girder_env/bin/activate`` to *enter* the new
virtual environment.  Inside the virtual environment you can use ``pip``,
``python``, and any other python script installed in your path as usual.
You can exit the virtual environment by running the shell function
``deactivate``.  The shell variable ``VIRTUAL_ENV`` will also list the
absolute path to the current virtual environment.  Entering a virtual
environment only persists for your current shell, so you must source
the activation script again whenever you wish to enter within a
new shell session.  Users and developers needing to work on several virtual
environments should consider using other packages that help manage them such as
`virtualenvwrapper <http://virtualenvwrapper.readthedocs.org/en/latest/index.html>`_,
`autoenv <https://github.com/kennethreitz/autoenv>`_,
`pyenv-virtualenv <https://github.com/yyuu/pyenv-virtualenv>`_, or
`pyenv-virtualenvwrapper <https://github.com/yyuu/pyenv-virtualenvwrapper>`_.


Install with pip
----------------

To install the Girder distribution from the python package index, simply run ::

    pip install girder

This will install the core Girder server as a site package in your system
or virtual environment. At this point, you might want to check the
:doc:`configuration <configuration>` to change your plugin and logging
paths.  In order to use the web interface, you must also install the web client
libraries. Girder installs a python script that will automatically build and
install these libraries for you. Just run the following command: ::

   girder-install web

.. note:: Installing the web client code requires the node package manager (npm).
   See the :doc:`prerequisites` section for instructions on installing nodejs.

.. note:: If you installed Girder into your system ``site-packages``, you may
   need to run the above commands as root.

Once this is done, you are ready to start using Girder as described in this
section: :ref:`run-girder`.

Installing extra dependencies with pip
--------------------------------------

Girder comes bundled with a number of :doc:`plugins` that require extra python
dependencies in order to use.  By default, none of these dependencies will be
installed; however, you can tell pip to install them using pip's
"`extras`_ " syntax.  Each girder plugin requiring extra python dependencies
can be specified during the pip install.  For example, installing girder with
support for the `celery_jobs` and `geospatial` plugins can be done like this: ::

   pip install girder[celery_jobs,geospatial]

There is also an extra you can use to install the depencies for all bundled
plugins supported in the current python environment called ``plugins``: ::

   pip install girder[plugins]

.. warning:: Not all plugins are available in every python version and platform.
   Specifying a plugin for in an unsupported environment will raise an error.

.. _extras: https://packaging.python.org/en/latest/installing/#installing-setuptools-extras

Install from Git Checkout
-------------------------

Obtain the Girder source code by cloning the Git repository on
`GitHub <https://github.com>`_: ::

    git clone https://github.com/girder/girder.git
    cd girder

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

    npm install && npm run build

This will run multiple `Grunt <http://gruntjs.com>`_ tasks, to build all of
the Javascript and CSS files needed to run the web client application.

.. _run-girder:

Run
---

To run the server, first make sure the Mongo daemon is running. To manually start it, run: ::

    mongod &

If you installed with pip, you will have the ``girder-server`` executable on your
path and can simply call ::

    girder-server

**- or -**

If you checked out the source tree, you can start the server with the
following command, which will have identical behavior: ::

    python -m girder

Then open http://localhost:8080/ in your web browser, and you should see the application.

Initial Setup
-------------

The first user to be created in the system is automatically given admin permission
over the instance, so the first thing you should do after starting your instance for
the first time is to register a user. After that succeeds, you should see a link
appear in the navigation bar that says ``Admin console``.

The next recommended action is to enable any plugins you want to run on your server.
Click the ``Admin console`` navigation link, then click ``Plugins``. Here, you
can turn plugins on or off. Whenever you change the set of plugins that are
enabled, you must restart the `CherryPy <http://www.cherrypy.org>`_ server for
the change to take effect. For information about specific plugins, see the
:ref:`Plugins <plugins>` section.

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

     girder-install -s plugin /path/to/your/plugin

Enabled plugins installed with ``-s`` may be edited in place and those changes will
be reflected after a server restart.
