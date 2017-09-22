
Developer Installation Guide
============================

If you wish to develop Girder or Girder plugins, you can either
:ref:`install Girder natively <native_install>` on your machine or
:ref:`inside a virtual machine (VM) <vagrant_install>` with Vagrant.

.. _native_install:

Native Installation
+++++++++++++++++++

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

Enter the virtual environment:

.. code-block:: none

   . ~/girder_env/bin/activate

The ``(girder_env)`` prepended to your prompt indicates you have *entered*
the virtual environment. Inside the virtual environment you can use ``pip``,
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



Install from Git repository
---------------------------

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

If you plan to use Girder's web client, you'll need to build it first. Run: ::

    girder-install web --dev

This will run multiple `Grunt <http://gruntjs.com>`_ tasks, to build all of
the Javascript and CSS files needed to run the web client application.

.. _run-girder:

Run
---

To run the server, first make sure the Mongo daemon is running. To manually start it, run: ::

    mongod &

Then to run Girder itself, just use the following command: ::

    girder-server

Then open http://localhost:8080/ in your web browser, and you should see the application.

Initial Setup
-------------

Admin Console
*************

The first user to be created in the system is automatically given admin permission
over the instance, so the first thing you should do after starting your instance for
the first time is to register a user. After that succeeds, you should see a link
appear in the navigation bar that says ``Admin console``.

Enable Plugins
**************

The next recommended action is to enable any plugins you want to run on your server.
Click the ``Admin console`` navigation link, then click ``Plugins``. Here, you
can turn plugins on or off. Whenever you change the set of plugins that are
enabled, you need to press the **Rebuild and restart** button at the top of the
Plugins page to rebuild the web client and restart the server to apply the change.

For information about specific plugins, see the :ref:`Plugins <plugins>` section.

Create Assetstore
*****************

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

.. _vagrant_install:

Virtual Machine
+++++++++++++++

The easiest way to develop for Girder is within a VM using Vagrant.
For this, you need `Vagrant <https://www.vagrantup.com/downloads.html>`_ and `VirtualBox <https://www.virtualbox.org/wiki/Downloads>`_.
Girder is tested to work seamlessly with Vagrant 2.0 and VirtualBox 5.1.

Once you have those installed, obtain the Girder source code by cloning the Git
repository on `GitHub <https://github.com/girder/girder>`_:

.. code-block:: bash

    git clone https://github.com/girder/girder.git
    cd girder

Inside of the Girder directory, simply run:

.. code-block:: bash

    vagrant up

This creates a VM running Ubuntu 14.04, then automatically installs Girder
within it. After it completes, Girder will be up and running at
http://localhost:9080/ on the host machine.

The VM is linked to your local Girder directory, so changes made locally will
impact the Girder instance running in the VM.

To access the VM, run from the Girder directory:

.. code-block:: bash

    vagrant ssh

This takes you inside the VM. From here, you might want to restart the server:

.. code-block:: bash

    sudo service girder restart

To rebuild the web client:

.. code-block:: bash

    girder-install web --dev

For more development documentation, see `During Development <development.html#during-development>`__
