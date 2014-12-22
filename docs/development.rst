Developer Guide
===============

Girder is a platform-centric web application whose client and server are very
loosely coupled. As such, development of Girder can be divided into the server
(a CherryPy-based Python module) and the primary client (a Backbone-based) web
client. This section is intended to get prospective contributors to understand
the tools used to develop Girder.

Configuring Your Development Environment
----------------------------------------

In order to develop Girder, you can refer to the :doc:`prerequisites` and
:doc:`installation` sections to setup a local development environment. Once
Girder is started via ``python -m girder``, the server will reload itself
whenever a Python file is modified.

To get the same auto-building behavior for JavaScript, we use ``grunt-watch``.
Thus, running ``grunt watch`` in the root of the repository will watch for
JavaScript, Stylus, and Jade changes in order to rebuild them on-the-fly. If you
do not run ``grunt watch`` while making code changes, you will need to run the
``grunt`` command to manually rebuild the web client in order to see your changes
reflected.

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
view object, set the ``parentView`` to ``null``.


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

Running the Tests with Coverage Tracing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run Python coverage on your tests, configure with CMake and run CTest.
The coverage data will be automatically generated. After the tests are run,
you can find the HTML output from the coverage tool in the source directory
under **/clients/web/dev/built/py_coverage**.


Creating a new release
----------------------

Girder releases are uploaded to `PyPI <https://pypi.python.org/pypi/girder>`_
for easy installation via ``pip``.  In addition, the python source package and
optional plugin and web client packages are stored as releases inside the
official `github repository <https://github.com/girder/girder/releases>`_.
The recommended process for generating a new release is described here.

1.  From the target commit, set the desired version number in ``package.json``
    and ``docs/conf.py``.  Create a new commit and note the SHA; this will
    become the release tag.

2.  Ensure that all tests pass.

3.  Clone the repository in a new directory and checkout the release SHA.
    (Packaging in an old directory could cause files and plugins to be
    mistakenly included.)

4.  Run ``npm install && grunt package``.  This will generate three
    new tarballs in the current directory:

     ``girder-<version>.tar.gz``
         This is the python source distribution for the core server API.
     ``girder-web-<version>.tar.gz``
         This is the web client libraries.
     ``girder-plugins-<version>.tar.gz``
         This contains all of the plugins in the main repository.

5.  Create a new virtual environment and install the python package into
    it as well as the optional web and plugin components.  This should
    not be done in the repository directory because the wrong Girder
    package will be imported.  ::

        mkdir test && cd test
        virtualenv release
        source release/bin/activate
        pip install ../girder-<version>.tar.gz
        girder-install web -s ../girder-web-<version>.tar.gz
        girder-install plugin -s ../girder-plugins-<version>.tar.gz

6.  Now start up the Girder server and ensure that you can browse
    the web client, plugins, and swagger docs.

7.  When you are confident everything is working correctly, generate
    a `new release <https://github.com/girder/girder/releases/new>`_
    on GitHub.  You must be
    sure to use a tag version of ``v<version>``, where ``<version>``
    is the version number as it exists in ``package.json``.  For
    example, ``v0.2.4``.  Attach the three tarballs you generated
    to the release.

8.  Add the tagged version to `readthedocs <https://readthedocs.org/projects/girder/>`_
    and make sure it builds correctly.

9.  Finally, upload the release to PyPI with the following command: ::

        python setup.py sdist upload
