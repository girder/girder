# Server Side Testing

## Running the tests

Before you can run the tests, you'll need to configure the project with CMake.

    mkdir ../girder-build
    cd ../girder-build
    cmake ../girder

You only need to do that once. From then on, whenever you want to run the tests, just:

    cd girder-build
    ctest

> **Note**: The *-v* flag is optional and can be omitted if you do not want verbose output.

## Creating tests

The server side python tests are run using
[unittest](http://docs.python.org/2/library/unittest.html). All of the actual test cases are
stored under [server/test/cases](cases).

### Adding to an existing test case

If you want to add tests to an existing test case, just create a new function in the relevant
TestCase class. The function name must start with **test**. If the existing test case has **setUp**
or **tearDown** methods, be advised that those methods will be run before and after *each* of
the test methods in the class.

### Creating a new test case

To create an entirely new test case, create a new file in **cases** that ends with **_test.py**.
To start off, put the following code in the module (with appropriate class name of course):

    from .. import base

    def setUpModule():
        base.startServer()

    def tearDownModule():
        base.stopServer()

    class MyTestCase(base.TestCase):

> **Note**: If your test case does not need to communicate with the server, you don't need to
> call base.startServer() and base.stopServer() in the setUpModule() and tearDownModule()
> functions. Those functions are called once per module rather than once per test method.

Then, in the **MyTestCase** class, just add functions that start with **test**, and they will
automatically be run by unittest.

Finally, you'll need to register your test in the [CMakeLists.txt](CMakeLists.txt) file in
this directory. Just add a line like the ones already there. For example, if the test file you
created was called module_test.py, you would add:

    add_test(ModuleName module)

Re-run cmake in the build directory, and then run ctest, and your test will be run.
