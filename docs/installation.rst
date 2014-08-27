Installation
============

Before you install, see the :doc:`prerequisites` guide to make sure you
have all required system packages installed.

To run the server, you must install some external python package
dependencies: ::

    pip install -r requirements.txt

.. note:: If you intend to develop Girder or want to run the test suite, you should also
   install the development dependencies: ::

        pip install -r requirements-dev.txt

Before you can build the client-side code project, you must install the
`Grunt <http://gruntjs.com>`_ command line utilities: ::

    npm install -g grunt grunt-cli

Then cd into the root of the repository and run: ::

    npm install

Finally, when all node packages are installed, run: ::

    grunt init

Build
-----

To build the client side code, run the following command from within the
repository: ::

    grunt

Run this command any time you change a JavaScript or CSS file under
`__clients/web__.`

Run
---

To run the server, first make sure the mongo daemon is running. To manually start it, run: ::

    mongod &

Then, just run: ::

    python -m girder

Then open http://localhost:8080/ in your web browser, and you should see the application. ::

Initial Setup
-------------

The first user to be created in the system is automatically given admin permission
over the instance, so the first thing you should do after starting your instance for
the first time is to register a user. After that succeeds, you should see a link
appear in the navigation bar that says ``Admin console``.

The next recommended action is to enable any plugins you want to run on your server.
Click the ``Admin console`` navigation link, then click ``Plugins``. Here, you
can turn plugins on or off. Whenever you change the set of plugins that are
enabled, you must restart the cherrypy server in order for the change to take
effect. For information about specific plugins, see the :ref:`Plugins <plugins>` section.

After you have enabled any desired plugins and restarted the server, the next
recommended action is to create an ``Assetstore`` for your system. No users
can upload data to the system until an assetstore is created, since all files
in Girder must reside within an assetstore. See the :ref:`Assetstores <assetstores>` section
for a brief overview of ``Assetstores``.
