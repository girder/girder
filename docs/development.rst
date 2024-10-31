Developer Guide
===============

Girder is a platform-centric web application whose client and server are very
loosely coupled. As such, development of Girder can be divided into the server
(a CherryPy-based Python module) and the primary client (a Backbone-based) web
client. This section is intended to get prospective contributors to understand
the tools used to develop Girder.

Configuring Your Development Environment
----------------------------------------

Next, you should install the Python development dependencies with pip, to
provide helpful development tools and to allow the test suite to run: ::

    pip install -r requirements-dev.txt

Install front-end web client development dependencies and build the web client code: ::

    cd girder/web && yarn && yarn build

This will build the core web client. Any plugins you plan to install that have front-end code
will need to be built as well. For example, to build the jobs plugin: ::

    cd plugins/jobs/girder_jobs/web_client && yarn && yarn build

Finally, you'll want to set your server into development mode. Add the following entry into your
local config file (see :ref:`Configuration <configuration>` for instructions):

.. code-block:: ini

    [server]
    mode="development"

Girder Shell
^^^^^^^^^^^^

To test various functionality in a typical REPL (Python, IPython, etc) some bootstrapping
is required to configure the Girder server. This sets up an "embedded" server, meaning no TCP ports
are actually bound but requests can still be performed via Python. Bootstrapping the server
involves running ``girder.utility.server.configureServer`` with the plugins to be enabled.

Girder provides a utility script for entering into a shell with the server preconfigured. Once
Girder is installed the script can be run using ``girder shell`` which optionally takes a comma
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
Girder. Rather, create a custom **girder.cfg** file and place it in one of the supported
locations (see :ref:`Configuration <configuration>`). You only need to edit the
values in the file that you wish to change from their default values; the system
loads the **dist** file first, then the custom file, so your local settings
will override the defaults.

.. _client_development_js:

Client Development
------------------

If you are writing a custom client application that communicates with the Girder
REST API, you should look at the Swagger page that describes all of the available
API endpoints. The Swagger page can be accessed by navigating a web browser to
``/api/v1``. If you wish to consume the Swagger-compliant
API specification programmatically, the JSON listing is served out of ``/api/v1/describe``.

If you are working on the main Girder web client, either in core or extending it via
plugins, there are a few conventions that should be followed. Namely, if you write
code that instantiates new ``View`` descendant objects, you should pass a
``parentView`` property when constructing it. This will allow the child view to
be cleaned up recursively when the parent view is destroyed. If you forget to set
the ``parentView`` property when constructing the view, the view will still work as
expected, but a warning message will appear in the console to remind you. Example:

.. code-block:: javascript

    import View from '@girder/core/views/View';

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
Most of Girder's server tests are run via `tox <https://tox.readthedocs.io/en/latest/>`_, which
provides virtual environment isolation and automatic dependency installation for test environments.
The ``tox`` Python package must be installed:

.. code-block:: bash

   pip install tox

To run the basic test suite, ensure that a MongoDB instance is ready on ``localhost:27017``,
then run:

.. code-block:: bash

   tox

To destroy and recreate all virtual environments used for testing, pass the ``-r`` flag to ``tox``.

Static Analysis Tests
^^^^^^^^^^^^^^^^^^^^^
Girder's static analysis (linting) tests are fast to execute, run on all code, and don't require
a running MongoDB. It's recommended to run them locally before any Python code changes are
committed. To execute them, run:

.. code-block:: bash

   tox -e lint

pytest Tests
^^^^^^^^^^^^
Girder's modern automated tests are written with `pytest <https://docs.pytest.org/en/stable/>`_.
To execute them, ensure MongoDB is ready, then run:

.. code-block:: bash

   tox -e pytest

Specific arguments can be passed through ``tox`` to ``pytest`` by adding them after a ``--``.

For example, ``pytest`` uses ``-k`` to filter tests; to run only the ``testLoadModelDecorator``
test, run:

.. code-block:: bash

   tox -e pytest -- -k testLoadModelDecorator

Legacy unittest Tests
^^^^^^^^^^^^^^^^^^^^^
Girder's legacy automated tests are written with Python's
`unittest framework <https://docs.python.org/3/library/unittest.html>`_ and executed with
`CMake <http://www.cmake.org>`_. All new tests should be written with pytest, but many important
test cases are still covered only by unitest.

.. note:: Unless debugging code that is already coverered by a legacy test case, it may be more
          convenient to allow these tests to be run by Girder's CI environment, instead of
          configuring them locally.

To initialize the legacy tests, from the root ``girder`` repo, run:

.. code-block:: bash

   mkdir ../girder-build
   cd ../girder-build
   cmake ../girder
   make

You only need to do this once. From then on, whenever you want to run the tests, run:

.. code-block:: bash

   cd girder-build
   ctest

There are many ways
`to filter tests when running CTest <http://www.cmake.org/cmake/help/v3.0/manual/ctest.1.html>`_
or run the tests in parallel. For example, this command will run tests with name matches regex
**server_user** with verbose output:

.. code-block:: bash

   ctest -V -R server_user

Client Side Testing
-------------------
Static Analysis Tests
^^^^^^^^^^^^^^^^^^^^^
To run static analysis tests on client side code, run from the top-level Girder directory:

.. code-block:: bash

   npm i
   npm run lint

Running the client end-to-end tests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Girder's web client test suite are setup as end-to-end tests that make use of an actual server
and database. To run them, make sure you are within your Girder virtual environment, and make sure
`mongod` is running locally on port 27017. You'll also need to make sure you've built all the plugin
web client code, which can be done with:

.. code-block:: bash

    python .circleci/build_plugins.py ./plugins

Once that is done, then run:

.. code-block:: bash

    cd girder/web
    npm i
    npm run test


Adding a New Client Side Test
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To add a new client side test, add a new spec file in ``girder/web/test/spec/``. We recommend
copying an existing test case for setting up the server, and then using VSCode's Playwright plugin
to record your interactions.

Test Coverage Reporting
-----------------------
When Girder's full test suite is run in the CI environment, a test coverage report for both
server and client code is generated and uploaded to Codecov. This may be
`viewed online at any time <https://codecov.io/gh/girder/girder>`_.

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

1. Ensure that you are using a development environment with version >=5.6 of npm installed:

   .. code-block:: bash

       npm install -g 'npm@>=5.6'

2. Update ``girder/web_client/package.json.template`` or ``girder/web_client/src/package.json`` to
   add a new *abstract* specifier for the package:

  * Packages that are bundled into the web client must be listed under the ``dependencies`` field
    of ``girder/web_client/src/package.json`` and should generally use the
    `tilde range <https://www.npmjs.com/package/semver#tilde-ranges-123-12-1>`_
    to specify versions.
  * Packages that are part of the build or testing process should be listed under either the
    ``dependencies`` or ``devDependencies`` fields of ``girder/web_client/package.json.template``
    and should generally use the
    `caret range <https://www.npmjs.com/package/semver#caret-ranges-123-025-004>`_
    to specify versions.

If updating npm libraries related to linting or documentation, you should instead modify
the top-level ``package.json`` file, run ``npm update``, then commit the modified files.

Creating a new release
----------------------

Girder releases are uploaded to `PyPI <https://pypi.python.org/pypi/girder>`_
for easy installation via ``pip``. Each time a pull request is merged to master, an incremental
"dev" release is created during CI as a pre-release package and published to PyPI, making it easy
for downstreams to install bleeding edge packages without needing to clone the Girder repository.

The major, minor, and patch version are inferred automatically using
`setuptools-scm <https://pypi.org/project/setuptools-scm/>`_ based on the latest git tag. Hence,
creating a new release is as simple as pushing a new git tag. For example, from the target commit,
you could simply run:

.. code-block:: bash

   git tag v4.5.6
   git push --tags

That will trigger CircleCI to run, and if all tests pass, the 4.5.6 release will be uploaded to PyPI.
