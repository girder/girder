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
JavaScript, Stylus, and Jade changes in order to rebuild them on-the-fly.

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

Sending Emails
^^^^^^^^^^^^^^

Girder has utilities that make it easy to send emails. For the sake of
maintainability and reusability of the email content itself, emails are stored
as `Mako templates <http://www.makotemplates.org/>`_ in the
**girder/mail_templates** directory. By convention, email templates should
include ``_header.mako`` above and ``_footer.mako`` below the content. If you wish
to send an email from some point within the application, you can use the
utility functions within ``girder.utility.mail_utils``, as in the example
below: ::

    from girder.utility import mail_utils

    ...

    def my_email_sending_code():
        html = mail_utils.renderTemplate('myContentTemplate.mako', {
            'param1': 'foo',
            'param2': 'bar'
        })
        mail_utils.sendEmail(to=email, subject='My mail from girder', text=html)

If you wish to send email from within a plugin, simply create a
**server/mail_templates** directory within your plugin, and it will be
automatically added to the mail template search path when your plugin is loaded.
To avoid name collisions, convention dictates that mail templates within your
plugin should be prefixed by your plugin name, e.g.,
``my_plugin.my_template.mako``.

.. note:: All emails are sent as rich text (``text/html`` MIME type).

Client Development
------------------

If you are writing a custom client application that communicates with the Girder
REST API, you should look at the Swagger page that describes all of the available
API endpoints. The Swagger page can be accessed by navigating a web browser to
``api/v1`` relative to the server root. If you wish to consume the Swagger-compliant
API specification programmatically, the JSON listing is served out of ``api/v1/describe``.

Authenticating to the web API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Clients can make authenticated web API calls by passing a secure temporary token
with their requests. Tokens are obtained via the login process; the standard
login process requires the client to make an HTTP ``GET`` request to the
``api/v1/user/authentication`` route, using HTTP Basic Auth to pass the user
credentials. For example, for a user with login "john" and password "hello",
first base-64 encode the string ``"john:hello"`` which yields ``"am9objpoZWxsbw=="``.
Then take the base-64 encoded value and pass it via the ``Authorization`` header: ::

    Authorization: Basic am9objpoZWxsbw==

If the username and password are correct, you will receive a 200 status code and
a JSON document from which you can extract the authentication token, e.g.: ::

    {
      "authToken": {
        "token": "urXQSHO8aF6cLB5si0Ch0WCiblvW1m8YSFylMH9eqN1Mt9KvWUnghVDKQy545ZeA",
        "expires": "2015-04-11 00:06:14.598570"
      },
      "message": "Login succeeded.",
      "user": {
        ...
      }
    }

The ``authToken.token`` string is the token value you should pass in subsequent API
calls, which should either be passed as the ``token`` parameter in the query or
form parameters, or as the value of a custom HTTP header with the key ``Girder-Token``, e.g. ::

    Girder-Token: urXQSHO8aF6cLB5si0Ch0WCiblvW1m8YSFylMH9eqN1Mt9KvWUnghVDKQy545ZeA

.. note:: When logging in, the token is also sent to the client in a Cookie header so that web-based
   clients can persist its value conveniently for its duration. However, for security
   reasons, merely passing the cookie value back is not sufficient for authentication.

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

Creating Tests
^^^^^^^^^^^^^^

The server side Python tests are run using
`unittest <https://docs.python.org/2/library/unittest.html>`_. All of the actual
test cases are stored under `tests/cases`.

Adding to an Existing Test Case
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to add tests to an existing test case, just create a new function
in the relevant TestCase class. The function name must start with **test**. If
the existing test case has **setUp** or **tearDown** methods, be advised that
those methods will be run before and after *each* of the test methods in the
class.

Creating a New Test Case
^^^^^^^^^^^^^^^^^^^^^^^^

To create an entirely new test case, create a new file in **cases** that ends
with **_test.py**. To start off, put the following code in the module (with
appropriate class name of course):

.. code-block:: python

    from .. import base

    def setUpModule():
        base.startServer()

    def tearDownModule():
        base.stopServer()

    class MyTestCase(base.TestCase):

.. note:: If your test case does not need to communicate with the server, you
   do not need to call **base.startServer()** and **base.stopServer()** in the
   **setUpModule()** and **tearDownModule()** functions. Those functions are called
   once per module rather than once per test method.

Then, in the **MyTestCase** class, just add functions that start with **test**,
and they will automatically be run by unittest.

Finally, you'll need to register your test in the `CMakeLists.txt` file in the
`tests` directory. Just add a line like the ones already there at the bottom.
For example, if the test file you created was called `thing_test.py`, you would
add:

.. code-block:: cmake

    add_python_test(thing)

Re-run CMake in the build directory, and then run CTest, and your test will be
run.

.. note:: By default, **add_python_test** allows the test to be run in parallel
   with other tests, which is normally fine since each python test has its own
   assetstore space and its own mongo database, and the server is typically
   mocked rather than actually binding to its port. However, some tests (such
   as those that actually start the cherrypy server) should not be run concurrently
   with other tests that use the same resource. If you have such a test, use the
   ``RESOURCE_LOCKS`` argument to **add_python_test**. If your test requires the
   cherrypy server to bind to its port, declare that it locks the ``cherrypy``
   resource. If it also makes use of the database, declare that it locks the
   ``mongo`` resource. For example: ::

       add_python_test(my_test RESOURCE_LOCKS cherrypy mongo)

Creating a new release
^^^^^^^^^^^^^^^^^^^^^^

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
