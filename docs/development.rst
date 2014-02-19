Developing Girder
=================

Girder is a platform-centric web application whose client and server are very
loosely coupled. As such, development of girder can be divided into the server
(a cherrypy-based python module) and the primary client (a backbone-based) web
client. This section is intended to get prospective contributors to understand
the tools used to develop Girder.

Server Side Testing
-------------------

Running the tests
^^^^^^^^^^^^^^^^^

Before you can run the tests, you'll need to install
`pep8 <http://www.python.org/dev/peps/pep-0008/>`_ for Python style
checking. ::

    pip install pep8

Also, you'll need to configure the project with CMake. ::

    mkdir ../girder-build
    cd ../girder-build
    cmake ../girder

You only need to do that once. From then on, whenever you want to run the
tests, just: ::

    cd girder-build
    ctest

There are many ways to filter tests when running CTest, or run the tests in
parallel. More information about CTest can be found
`here <http://www.cmake.org/cmake/help/v2.8.8/ctest.html>`_.

Running the tests with coverage tracing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to run coverage, make sure you have installed
`coverage.py <http://nedbatchelder.com/code/coverage/>`_: ::

    pip install coverage

And in your CMake configuration, set **PYTHON_COVERAGE** to **ON**. Then,
configure with cmake and run **ctest**, and the coverage will be created. After
the tests are run, you can find the HTML output from the coverage tool in the
source directory under **/clients/web/dev/built/py_coverage**.

Creating tests
^^^^^^^^^^^^^^

The server side python tests are run using
`unittest <http://docs.python.org/2/library/unittest.html>`_. All of the actual
test cases are stored under `tests/cases`.

Adding to an existing test case
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to add tests to an existing test case, just create a new function
in the relevant TestCase class. The function name must start with **test**. If
the existing test case has **setUp** or **tearDown** methods, be advised that
those methods will be run before and after *each* of the test methods in the
class.

Creating a new test case
^^^^^^^^^^^^^^^^^^^^^^^^

To create an entirely new test case, create a new file in **cases** that ends
with **_test.py**. To start off, put the following code in the module (with
appropriate class name of course): ::

    from .. import base

    def setUpModule():
        base.startServer()

    def tearDownModule():
        base.stopServer()

    class MyTestCase(base.TestCase):

.. note:: If your test case does not need to communicate with the server, you
   don't need to call base.startServer() and base.stopServer() in the
   setUpModule() and tearDownModule() functions. Those functions are called
   once per module rather than once per test method.

Then, in the **MyTestCase** class, just add functions that start with **test**,
and they will automatically be run by unittest.

Finally, you'll need to register your test in the `CMakeLists.txt` file in the
`tests` directory. Just add a line like the ones already there at the bottom.
For example, if the test file you created was called thing_test.py, you would
add: ::

    add_python_test(thing)

Re-run cmake in the build directory, and then run ctest, and your test will be
run.

Server Development
------------------

Developing the server can be done...

Client Development
------------------

Info goes here...
