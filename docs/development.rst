Developer Guide
===============

Girder is a platform-centric web application whose client and server are very
loosely coupled. As such, development of Girder can be divided into the server
(a CherryPy-based Python module) and the primary client (a Backbone-based) web
client. This section is intended to get prospective contributors to understand
the tools used to develop Girder.

Configuring Your Development Environment
----------------------------------------

In order to develop Girder, you should first refer to :doc:`prerequisites <prerequisites>`, `virtual environment <installation.html#creating-a-virtual-environment>`__, `install from Git <installation.html#install-from-git-repository>`__, and `run <installation.html#run>`__ sections to setup a basic local development environment.

Next, you should install the Python development dependencies with pip, to
provide helpful development tools and to allow the test suite to run: ::

    pip install -r requirements-dev.txt

Install front-end web client development dependencies. This will install npm modules eslint and pug-lint, which are needed to run tests. This will also build the web client code: ::

    girder-install web --dev

For more options for building the web client, run: ::

    girder-install web --help


Vagrant
^^^^^^^

A shortcut to going through the development environment configuration steps is
to use `Vagrant <https://www.vagrantup.com>`_ to setup the environment on a
`VirtualBox <https://www.virtualbox.org>`_ virtual machine. For more
documentation on how to set this up, see `Developer Installation <dev-installation.html>`__

.. seealso::

   For more information on provisioning Girder, see :doc:`provisioning`.


During Development
------------------

Once Girder is started via ``girder-server``, the server
will reload itself whenever a Python file is modified.

If you are doing front-end development, it's much faster to use a *watch* process to perform
automatic fast rebuilds of your code whenever you make changes to source files.

If you are making changes to Girder's core web client, run the following watch command: ::

    girder-install web --watch

If you are developing a web client of a plugin, run: ::

    girder-install web --watch-plugin your_plugin_name

With ``watch`` option, *sourcemaps* will be generated, which helps debugging front-end code in browser.
When you want to end the watch process, press Ctrl+C (or however you would normally terminate a
process in your terminal).

Girder Shell
^^^^^^^^^^^^

To test various functionality in a typical REPL (Python, IPython, etc) some bootstrapping
is required to configure the Girder server. This sets up an "embedded" server, meaning no TCP ports
are actually bound but requests can still be performed via Python. Bootstrapping the server
involves running ``girder.utility.server.configureServer`` with the plugins to be enabled.

Girder provides a utility script for entering into a shell with the server preconfigured. Once
Girder is installed the script can be run using ``girder-shell`` which optionally takes a comma
separated list of plugins to enable.

Utilities
---------

Girder has a set of utility modules and classes that provide handy extractions
for certain functionality. Detailed API documentation can be found :ref:`here <api-docs-utility>`.

Configuration Loading
^^^^^^^^^^^^^^^^^^^^^

The Girder configuration loader allows for lazy-loading of configuration values
in a CherryPy-agnostic manner. The recommended idiom for getting the config
object is: ::

    from girder.utility import config
    cur_config = config.getConfig()

There is a configuration file for Girder located in **girder/conf**. The file
**girder.dist.cfg** is the file distributed with the repository and containing
the default configuration values. This file should not be edited when deploying
Girder. Rather, edit the **girder.local.cfg** file. You only need to edit the
values in the file that you wish to change from their default values; the system
loads the **dist** file first, then the **local** file, so your local settings
will override the defaults.

.. _client_development_js:

Server Development
------------------

All commits to the core python code must work in both python 2.7 and 3.5.
Python code in plugins should also work in both, but some plugins may depend
on third party libraries that do not support python 3. If that is the case, those
plugins should declare ``"python3": false`` in their **plugin.json** or **plugin.yml** file
to indicate that they do not support being run in python 3. Automated testing of
those plugins should also be disabled for python3 if those tests would fail in a
python 3 environment. This can be achieved by passing an additional flag ``PY2_ONLY``
to ``add_python_test`` in your **plugin.cmake** file.

Python Style
^^^^^^^^^^^^

We use ``flake8`` to test for Python style on the server side.

Use ``%`` instead of ``format``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``%`` or some other string formatting operation that coerces to unicode,
and avoid ``format``, since it does not coerce to unicode and has caused bugs.


Client Development
------------------

If you are writing a custom client application that communicates with the Girder
REST API, you should look at the Swagger page that describes all of the available
API endpoints. The Swagger page can be accessed by navigating a web browser to
``api/v1`` relative to the server root. If you wish to consume the Swagger-compliant
API specification programmatically, the JSON listing is served out of ``api/v1/describe``.

If you are working on the main Girder web client, either in core or extending it via
plugins, there are a few conventions that should be followed. Namely, if you write
code that instantiates new ``View`` descendant objects, you should pass a
``parentView`` property when constructing it. This will allow the child view to
be cleaned up recursively when the parent view is destroyed. If you forget to set
the ``parentView`` property when constructing the view, the view will still work as
expected, but a warning message will appear in the console to remind you. Example:

.. code-block:: javascript

    import View from 'girder/views/View';

    MySubView = View.extend({
       ...
    });

    new MySubView({
        el: ...,
        otherProperty: ...,
        parentView: this
    });

If you use ``View`` in custom Backbone apps and need to create a new root
view object, set the ``parentView`` to ``null``. If you are using a Girder widget
in a custom app that does not use the ``View`` as the base object for
its views, you should pass ``parentView: null`` and make sure to call
``destroy()`` on the view manually when it should be cleaned up.


Server Side Testing
-------------------

Running the Tests with CTest
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note:: Girder is currently transitioning its Python testing to use `pytest <https://pytest.org>`_, until
          the transition is complete both ``ctest`` and ``pytest`` must be run to cover
          all tests. See the section below for running tests with ``pytest``.

First, you will need to configure the project with
`CMake <http://www.cmake.org>`_. ::

    mkdir ../girder-build
    cd ../girder-build
    cmake ../girder

You only need to do this once. From then on, whenever you want to run the
tests, just: ::

    cd girder-build
    ctest

There are many ways to filter tests when running CTest or run the tests in
parallel. For example, this command will run tests with name matches regex **server_user** with verbose output.
More information about CTest can be found
`here <http://www.cmake.org/cmake/help/v3.0/manual/ctest.1.html>`_. ::

    ctest -V -R server_user


If you run into errors on any of the packaging tests, two possible fixes are

1) run ``make`` inside your ``girder-build`` directory, which will create a special
virtualenv needed to build the packages.

2) delete any of the files generated by the packaging tests, which will be in your
source dir ``girder`` and could include ``girder-<version>.tar.gz``, ``girder-web-<version>.tar.gz``,
and ``girder-plugins-<version>.tar.gz``.


Running the Tests with pytest
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

From the Girder directory, run ``pytest``. To run specific tests with long tracebacks, run ::

  pytest --tb=long -k testTokenSessionDeletion


Running the Tests with Coverage Tracing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run Python coverage on your tests, configure with CMake and run CTest.
The coverage data will be automatically generated. After the tests are run,
you can find the HTML output from the coverage tool in the source directory
under **/clients/web/dev/built/py_coverage**.

Client Side Testing
-------------------

Using the same setup as above for the Server Side Tests, your environment will be set up
The client side tests and server side tests are both harnessed with CTest, so use the following commands to run both ::

    cd girder-build
    ctest

will run all of the tests, which include the client side tests.  Our client tests use the
Jasmine JS testing framework.

If you encounter errors regarding ESLINT or PUG_LINT, there is a chance you missed certain steps for setting up development dependencies.
You could use ``ccmake`` to change ``CMake`` configuration. Or, it might be easier to recreate the environment from the beginning.

When running client side tests, if you try to SIGINT (ctrl+c) the CTest process, CTest
won't pass that signal down to the test processes for them to handle.  This can result
in orphaned python unittest processes and can prevent future runs of client tests.  If you
run a client side test and see an error message similar to ``IOError: Port 30015 not free on '0.0.0.0'``,
then look for an existing process similar to ``/usr/bin/python2.7 -m unittest -v tests.web_client_test``,
kill the process, and then try your tests again.

Adding a New Client Side Test
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To add a new client side test, add a new spec file in ``/clients/web/test/spec/``, add a line
referencing your spec file to ``/girder/tests/CMakeLists.txt`` using the ``add_web_client_test`` function,
and then run in your build directory ::

    cmake ../girder

before running your tests.

An example of a very simple client side test would be as follows ::

    add_web_client_test(some_client_test "someSpec.js" PLUGIN "my_plugin")

The ``PLUGIN`` argument indicates that "my_plugin" is the owner of ``some_client_test``, at the time of the test my_plugin and all of its dependencies will be loaded.

If additional plugins are needed for a specific test, that can be achieved using the ``ENABLEDPLUGINS`` argument ::

    add_web_client_test(another_client_test "anotherSpec.js" PLUGIN "my_plugin" ENABLEDPLUGINS "my_plugin" "jobs")

Here ``ENABLEDPLUGINS`` ensures that my_plugin *and* the jobs plugin are loaded, along with their dependencies at the time of ``another_client_test``.

.. note:: Core functionality shouldn't depend on plugins being enabled, this test definition is more suitable for a plugin. Information for testing plugins can be found under :doc:`plugin-development`.

You will find many useful methods for client side testing in the ``girderTest`` object
defined at ``/clients/web/test/testUtils.js``.


Initializing the Database for a Test
------------------------------------

.. note:: This functionality has not yet been ported to our ``pytest`` tests.

When running tests in Girder, the database will initially be empty.  Often times, you want to be able to start the test with the database in a
particular state.  To avoid repetitive initialization code, Girder provides a way to import a folder hierarchy from the file system
using a simple initialization file.  This file is in YAML (or JSON) format and provides a list of objects to insert into the database
before executing your test.  A typical example of this format is as follows

.. code-block:: YAML

    ---
    users:
      - login: 'admin'
        password: 'password'
        firstName: 'First'
        lastName: 'Last'
        email: 'admin@email.com'
        admin: true
        import: 'files/user'

    collections:
      - name: 'My collection'
        public: true
        creator: 'admin'
        import: 'files/collection'

This will create one admin user and a public collection owned by that user.  Both the generated user and collection objects
will contain folders imported from the file system.  Relative paths provided by the ``import`` key will be resolved relative
to the location of the YAML file on disk.  You can also describe the full hierarchy in the YAML file itself for more complicated
use cases.  See the test spec in ``tests/cases/setup_database_test.yml`` for a more complete example.

.. note::

    When importing from a local path into a user or collection, files directly under that path are ignored because
    items can be only inserted under folders.

To use the initialization mechanism, you should add the YAML file next to your test file.  For example, if your test
is defined in ``tests/cases/my_test.py``, then the initialization spec should go in ``tests/cases/my_test.yml``.  This
file will be automatically detected and loaded before executing your test code.  This is true for both python and
javascript tests added in core or inside plugins.

The python module ``setup_database.py`` that generates the database can also be run standalone to help in development.  To use it,
you should point girder to an empty database ::

    GIRDER_MONGO_URI='mongodb://127.0.0.1:27017/mytest' python tests/setup_database.py tests/test_database/spec.yml

You can browse the result in Girder by running ::

    GIRDER_MONGO_URI='mongodb://127.0.0.1:27017/mytest' girder-server

.. note::

    The ``setup_database`` module is meant to provision fixures for tests **only**.  If you want to provision
    a Girder instance for deployment, see the `Girder ansible client <https://github.com/girder/girder/tree/master/devops/ansible/roles/girder/library>`_.


Ansible Testing
---------------

Girder provides infrastructure for using Ansible to provision machines to run and configure Girder and its various plugins. Vagrant is used to create development environments and spin up virtual machines as a means of testing the Ansible provisioning infrastructure.

.. seealso::

   Details for usage of our provisioning infrastructure can be found on :doc:`provisioning`.

Girder's Ansible infrastructure can be thought of as 2 components:
 1. The Girder Ansible Role (the ``girder_ansible`` CTest label)

    This is primarily responsible for *deploying* Girder

 2. The Girder Ansible Client (the ``girder_ansible_client`` CTest label)

    This is primarily responsible for *configuring* Girder through its REST API.


Testing the Ansible Role
^^^^^^^^^^^^^^^^^^^^^^^^

The Ansible role is tested simply by starting and provisioning a virtual machine with Vagrant and ensuring it returns a zero exit code.

The tests for these by default are running Vagrant with each of the Ansible playbooks in ``devops/ansible/examples``.

To test these one can run CMake with the ``ANSIBLE_TESTS`` option enabled, and test only the correct CTest label ::

  cmake -D ANSIBLE_TESTS=ON /path/to/girder
  ctest -L girder_ansible

.. note:: Since these tests require creating and provisioning several virtual machines, they take a long time to run which is why they're disabled by default.


Testing the Ansible Client
^^^^^^^^^^^^^^^^^^^^^^^^^^

The Ansible client is tested by provisioning a single Girder virtual machine and running Ansible playbooks against it.

To test these one can run CMake with the ``ANSIBLE_CLIENT_TESTS`` option enabled, and test only the correct CTest label ::

  cmake -D ANSIBLE_CLIENT_TESTS=ON /path/to/girder
  ctest -L girder_ansible_client

.. note:: Due to how dependencies are handled in CMake, it's currently not possible to individually run an Ansible Client test without also running the test that starts the virtual machine.


Code Review
-----------

Contributions to Girder are done via pull requests with a core developer
approving the PR with GitHub review system. At this point, the
topic branch can be merged to master. This is meant to be a simple,
low-friction process; however, code review is very important. It should be done
carefully and not taken lightly. Thorough code review is a crucial part of
developing quality software. When performing a code review, ask the following:

1.  Is the continuous integration server happy with this?
2.  Are there tests for this feature or bug fix?
3.  Is this documented (for users and/or developers)?
4.  Are the commits modular with good notes?
5.  Will this merge cleanly?
6.  Does this break backward compatibility? Is that okay?
7.  What are the security implications of this change? Does this open Girder up
    to any vulnerabilities (XSS, CSRF, DB Injection, etc)?


Third-Party Libraries
---------------------

Girder's standard procedure is to use a tool like
`piprot <https://github.com/sesh/piprot>`_ to check for out-of-date
third-party library requirements on a quarterly basis (typically near the dates
of the solstices and equinoxes). Library packages should generally be upgraded
to the latest released version, except when:

* Doing so would introduce any new unfixable bugs or regressions.
* Other closely-affiliated projects (e.g.
  `Romanesco <https://romanesco.readthedocs.org/>`_,
  `Minerva <https://minervadocs.readthedocs.org/>`_) use the same library *and*
  the other project cannot also feasibly be upgraded simultaneously.
* The library has undergone a major API change, and development resources do
  not permit updating Girder accordingly *or* Girder exposes parts of the
  library as members of Girder's API surface (e.g. CherryPy) and upgrading
  would cause incompatible API changes to be exposed. In this case, the library
  should still be upgraded to the highest non-breaking version that is
  available at the time.

.. note:: In the event that a security vulnerability is discovered in a
   third-party library used by Girder, the library *must* be upgraded to patch
   the vulnerability immediately and without regard to the aforementioned
   exceptions. However, attempts should still be made to maintain API
   compatibility via monkey patching, wrapper classes, etc.

Modifying core web client libraries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Web client libraries in Girder core are managed via `npm <https://www.npmjs.com/>`_.
When a new npm package is required, or an existing package is upgraded, the following
should be done:

1. Ensure that you are using a Linux development environment (macOS causes npm to produce slightly
   different outputs) with version >=5.3 of npm installed:

   .. code-block:: bash

       npm install -g 'npm@>=5.3'

2. Update ``dependencies`` or ``devDependencies`` in ``package.json`` to add a new
   *abstract* specifier for the package:

  * Packages that are bundled into the web client should generally use the
    `tilde range <https://www.npmjs.com/package/semver#tilde-ranges-123-12-1>`_
    to specify versions.
  * Packages that are part of the build or testing process should generally use the
    `caret range <https://www.npmjs.com/package/semver#caret-ranges-123-025-004>`_
    to specify versions.

3. Run from the root Girder directory:

   .. code-block:: bash

       npm update

4. Commit the updated ``package.json`` and ``package-lock.json`` files.

Creating a new release
----------------------

Girder releases are uploaded to `PyPI <https://pypi.python.org/pypi/girder>`_
for easy installation via ``pip``. In addition, the python source packages
are stored as releases inside the official
`github repository <https://github.com/girder/girder/releases>`_. The
recommended process for generating a new release is described here.

1.  From the target commit, set the desired version number in ``package.json``, ``clients/web/src/package.json``,
    and ``girder/__init__.py``. Create a new commit and note the SHA; this will
    become the release tag.

2.  Ensure that all tests pass.

3.  Clone the repository in a new directory and checkout the release SHA.
    (Packaging in an old directory could cause files and plugins to be
    mistakenly included.)

4.  Run ``python setup.py sdist --dist-dir=.``.  This will generate the source
    distribution tarball with a name like ``girder-<version>.tar.gz``.

5.  Create a new virtual environment and install the python package into
    it and build the web client. This should not be done in the repository
    directory because the wrong Girder package will be imported.  ::

        mkdir test && cd test
        virtualenv release
        source release/bin/activate
        pip install ../girder-<version>.tar.gz
        girder-install web

6.  Now start up the Girder server and ensure that you can browse the web
    client, plugins, and swagger docs.

7.  When you are confident everything is working correctly, generate
    a `new release <https://github.com/girder/girder/releases/new>`_
    on GitHub.  You must be sure to use a tag version of ``v<version>``, where
    ``<version>`` is the version number as it exists in ``package.json``.  For
    example, ``v0.2.4``.  Attach the tarball you generated to the release.

8.  Add the tagged version to `readthedocs <https://readthedocs.org/projects/girder/>`_
    and make sure it builds correctly.

9.  Finally, upload the release to PyPI with the following command: ::

        python setup.py sdist upload

10. Publish the new girder source package on npm.

        cd clients/web/src && npm publish

.. _releasepythonclientpackage:

Releasing the python client package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The design intent behind the python client package is to work with as many
versions of the Girder server as possible; think carefully before breaking this
compatibility. There isn't a formal rule for releasing versions of the python
client package, releases tend to be made when a significant change is made to
the client that people want to use in production.

Normal semantic versioning is not in use for the python client package because
its version is partially dependent on the Girder server package version. The
rules for versioning the python client package are as follows:

* The major version of the python client should be the same as the major version
  of the Girder server package, assuming it is compatible with the server API.
* The minor version should be incremented if there is any change in backward
  compatibility within the python client API, or if significant new features
  are added.
* If the release only includes bug fixes or minor enhancements, just increment
  the patch version token.

The process for releasing the python client is as follows:

1.  Set the version number inside ``clients/python/girder_client/__init__.py`` according
    to the above rules. It is set in the line near the top of the file that looks like
    ``__version__ = 'x.y.z'``

2.  Change to the ``clients/python`` directory of the source tree and build the
    package using the following commands.

    .. code-block:: bash

        cd clients/python
        python setup.py sdist --dist-dir .

3.  That should have created the package tarball as ``girder-client-<version>.tar.gz``.
    Install it locally in a virtualenv and ensure that you can call the ``girder-cli``
    executable.

    .. code-block:: bash

        mkdir test && cd test
        virtualenv release
        source release/bin/activate
        pip install ../girder-client-<version>.tar.gz
        girder-cli

4.  Go back to the ``clients/python`` directory and upload the package to pypi:

    .. code-block:: bash

        cd ..
        python setup.py sdist upload
