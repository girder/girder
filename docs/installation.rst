Installation
============

Before you install, see the :doc:`prerequisites` guide to make sure you
have all required system packages installed.

Install with PIP
----------------

To install the girder distribution from the python package index, simply run ::

    pip install girder

This will install girder as a site package that can be run as specified in this
section: :ref:`run-girder`.

Install from Git Checkout
-------------------------

Obtain the Girder source code by cloning the Git repository on
`GitHub <https://github.com>`_: ::

    git clone https://github.com/girder/girder.git

To run the server, you must install some external Python package
dependencies: ::

    pip install -r requirements.txt

.. note:: If you intend to develop Girder or want to run the test suite, you should also
   install the development dependencies: ::

        pip install -r requirements-dev.txt

Before you can build the client-side code project, you must install the
`Grunt <http://gruntjs.com>`_ command line utilities: ::

    npm install -g grunt-cli

Then cd into the root of the repository and run: ::

    npm install

Finally, when all Node packages are installed, run: ::

    grunt init

Build
-----

To build the client-side code, run the following command from within the
repository: ::

    grunt

Run this command any time you change a JavaScript or CSS file under
`__clients/web__.`

.. _run-girder:

Run
---

To run the server, first make sure the Mongo daemon is running. To manually start it, run: ::

    mongod &

Then, just run: ::

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
