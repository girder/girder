Developer Guide
===============

Girder is a platform-centric web application whose client and server are very
loosely coupled. As such, development of Girder can be divided into the server
(a CherryPy-based Python module) and the primary client (a Backbone-based) web
client. This section is intended to get prospective contributors to understand
the tools used to develop Girder.

Configuring Your Development Environment
----------------------------------------

In order to develop Girder, you should first refer to the :doc:`prerequisites`
and :doc:`installation` sections to setup a basic local environment.

Next, you should install the Python development dependencies, to
provide helpful development tools and to allow the test suite to run: ::

    pip install -r requirements-dev.txt

During development, once Girder is started via ``python -m girder``, the server
will reload itself whenever a Python file is modified.

Girder's web-based client application is built using the `Grunt <http://gruntjs.com/>`_
task running tool. When you run the ``npm install`` command during Girder's
installation, it will run all of the grunt tasks required to build the web client.
Grunt tasks are run with the ``grunt`` executable, which is installed under your Girder source
directory in the ``./node_modules/.bin/`` directory. You could conveniently update the
``PATH`` by running ``export PATH=$(pwd)/node_modules/.bin:$PATH`` -- once you do that,
you can just type ``grunt`` in your shell to run tasks.

.. note :: Alternatively, you could install the grunt command line interface globally so
   that the ``grunt`` command is automatically added to your ``PATH``. If you want to do
   that, run ``npm install -g grunt-cli``. Note that this command requires ``sudo`` on many
   systems.

It is recommended during development to make use of the ``grunt-watch`` tool. Running
``grunt watch`` in the root of the repository will watch for JavaScript, Stylus, and
Jade changes in order to rebuild them on-the-fly. If you do not run ``grunt watch``
while making code changes, you will need to run the ``grunt`` command to manually
rebuild the web client in order to see your changes reflected.

Note that some browser debugging tools do not play well with local variable
mangling in JavaScript. If you want to use such a debugger and need to work around this,
run ``grunt`` or ``grunt watch`` with the additional argument ``--debug-js``.
This will prevent name mangling in the minified output.

Vagrant
^^^^^^^

A shortcut to going through the installation steps for development is to use
`Vagrant <https://www.vagrantup.com>`_ to setup the environment on a
`VirtualBox <https://www.virtualbox.org>`_ virtual machine. To setup this
environment run ``vagrant up`` in the root of the repository. This will spin up
and provision a virtual machine, provided you have Vagrant and VirtualBox
installed. Once this process is complete, you can run ``vagrant ssh`` in order
to start Girder. There is a helper script in the Vagrant home directory that
will start Girder in a detached screen session. You may want to run a similar
process to run ``grunt watch`` as detailed above.

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

All commits to the core python code must work in both python 2.7 and 3.4.
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
code that instantiates new ``girder.View`` descendant objects, you should pass a
``parentView`` property when constructing it. This will allow the child view to
be cleaned up recursively when the parent view is destroyed. If you forget to set
the ``parentView`` property when constructing the view, the view will still work as
expected, but a warning message will appear in the console to remind you. Example:

.. code-block:: javascript

    MySubView = girder.View.extend({
       ...
    });

    new MySubView({
        el: ...,
        otherProperty: ...,
        parentView: this
    });

If you use ``girder.View`` in custom Backbone apps and need to create a new root
view object, set the ``parentView`` to ``null``. If you are using a Girder widget
in a custom app that does not use the ``girder.View`` as the base object for
its views, you should pass ``parentView: null`` and make sure to call
``destroy()`` on the view manually when it should be cleaned up.


Server Side Testing
-------------------

Running the Tests
^^^^^^^^^^^^^^^^^

First, you will need to configure the project with
`CMake <http://www.cmake.org>`_. ::

    mkdir ../girder-build
    cd ../girder-build
    cmake ../girder

You only need to do this once. From then on, whenever you want to run the
tests, just: ::

    cd girder-build
    ctest

There are many ways to filter tests when running CTest, or run the tests in
parallel. More information about CTest can be found
`here <http://www.cmake.org/cmake/help/v3.0/manual/ctest.1.html>`_.

If you run into errors on any of the packaging tests, two possible fixes are

1) run ``make`` inside your ``girder-build`` directory, which will create a special
virtualenv needed to build the packages.

2) delete any of the files generated by the packaging tests, which will be in your
source dir ``girder`` and could include ``girder-<version>.tar.gz``, ``girder-web-<version>.tar.gz``,
and ``girder-plugins-<version>.tar.gz``.

Running the Tests with Coverage Tracing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run Python coverage on your tests, configure with CMake and run CTest.
The coverage data will be automatically generated. After the tests are run,
you can find the HTML output from the coverage tool in the source directory
under **/clients/web/dev/built/py_coverage**.

Client Side Testing
-------------------

Using the same setup as above for the Server Side Tests, your environment will be set up
to run client side tests. Running ::

    cd girder-build
    ctest

will run all of the tests, which include the client side tests.  Our client tests use the
Jasmine JS testing framework.

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


Code Review
-----------

Contributions to Girder are done via pull requests with a core developer
accepting a PR by saying it "Looks good to me" or LGTM. At this point, the
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


Creating a new release
----------------------

Girder releases are uploaded to `PyPI <https://pypi.python.org/pypi/girder>`_
for easy installation via ``pip``. In addition, the python source packages
are stored as releases inside the official
`github repository <https://github.com/girder/girder/releases>`_. The
recommended process for generating a new release is described here.

1.  From the target commit, set the desired version number in ``package.json``
    and ``girder/__init__.py``. Create a new commit and note the SHA; this will
    become the release tag.

2.  Ensure that all tests pass.

3.  Clone the repository in a new directory and checkout the release SHA.
    (Packaging in an old directory could cause files and plugins to be
    mistakenly included.)

4.  Run ``npm install && grunt package``.  This will generate the source
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

Releasing the python client package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Whenever the main Girder package is released, the python client package should also
be versioned and released if is has changed since the last Girder release or the last
time it was released. Normal semantic versioning is not in use for the python client
package because its version is partially dependent on the Girder server package
version. The rules for versioning the python client package are as follows:

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
