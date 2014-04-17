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

.. note:: By default, **add_python_test** will run each python test serially
   by using the RESOURCE_LOCK capability of CTest. However, if it is OK for
   your test to be run in parallel with other python tests (i.e. it does not
   require a specific shared database state), then call add_python_test with
   the **NO_LOCK** option: ``add_python_test(thing NO_LOCK)``

Plugin Development
------------------

The capabilities of girder can be extended via plugins. The plugin framework is
designed to allow girder to be as flexible as possible, on both the client
and server sides. ::

A plugin is self-contained in a single directory. To create your plugin, simply
create a directory within the **plugins** directory. In fact, that directory
is the only thing that is truly required to make a plugin in girder. All of the
other components discussed henceforth are optional. ::

Example plugin
^^^^^^^^^^^^^^

We'll use a contrived example to demonstrate the capabilities and components of
a plugin. Our plugin will be called `cats`. ::

    cd plugins ; mkdir cats

The first thing we should do is create a **plugin.json** file in the **cats**
directory. As promised above, this file is not required, but is strongly
recommended by convention. This file contains high-level information about
your plugin. ::

    touch cats/plugin.json

This JSON file should specify a human-readable name and description for your
plugin, and can optionally contain a list of other plugins that your plugin
depends on. If your plugin has dependencies, the other plugins will be
enabled whenever your plugin is enabled. The contents of plugin.json for our
example will be: ::

    {
    "name": "My Cats Plugin",
    "description": "Allows users to manage their cats.",
    "dependencies": ["other_plugin"]
    }

This information will appear in the web client administration console, and
administrators will be able to enable and disable it there. Whenever plugins
are enabled or disabled, a server restart will be required in order for the
change to take effect. ::

Extending the server-side capabilities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Girder plugins can augment and alter the core functionality of the system in
almost any way imaginable. These changes can be achieved via several mechanisms
which are described below. First, in order to implement the functionality of
your plugin, create a **server** directory within your plugin, and make it
a python package by creating **__init__.py**. ::

    cd cats ; mkdir server ; touch server/__init__.py

This package will be imported at server startup if your plugin is enabled.
Additionally, if your package implements a ``load`` function, that will be
called. This ``load`` function is where the logic of extension should be
performed for your plugin. ::

    def load(info):
        ...

This ``load`` function must take a single argument, which is a dictionary of
useful information passed from the core system. This dictionary contains an
``apiRoot`` value, which is the object to which you should attach API endpoints,
a ``config`` value, which is the server's configuration dictionary, and a
``serverRoot`` object, which can be used to attach endpoints that do not belong
to the web API.

Adding a new route to the web API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to add a new route to an existing core resource type, just call the
``route()`` function on the existing resource type. For example, to add a
route for ``GET /item/:id/cat`` to the system, ::

    def myHandler(id, params):
        return {
           'itemId': id,
           'cat': params.get('cat', 'No cat param passed')
        }

    def load(info):
        info['apiRoot'].item.route('GET', (':id', 'cat'), myHandler)

When you start the server, you may notice a warning message appears:
``WARNING: No description docs present for route GET item/:id/cat``. You
can add self-describing API documentation to your route as in the following
example: ::

    from girder.api.describe import Description

    def myHandler(id, params):
        return {
           'itemId': id,
           'cat': params.get('cat', 'No cat param passed')
        }
    myHandler.description = (
        Description('Retrieve the cat for a given item.')
        .param('id', 'The item ID', paramType='path')
        .param('cat', 'The cat value.', required=False)
        .errorResponse())

That will make your route automatically appear in the swagger documentation
and will allow users to interact with it via that UI.

Adding a new resource type to the web API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Perhaps for our use case we determine that ``cat`` should be its own resource
type rather than being referenced via the ``item`` resource. If we wish to add
a new resource type entirely, it will look much like one of the core resource
classes, and we can add it to the API in the ``load()`` method. ::


    from girder.api.rest import Resource

    class Cat(Resource):
        def __init__(self):
            self.resourceName = 'cat'

            self.route('GET', (), self.findCat)
            self.route('GET', (':id',), self.getCat)
            self.route('POST', (), self.createCat)
            self.route('PUT', (':id',), self.updateCat)
            self.route('DELETE', (':id',), self.deleteCat)

        def getCat(self, id, params):
            ...

    def load(info):
        info['apiRoot'].cat = Cat()

The events system
^^^^^^^^^^^^^^^^^

In addition to being able to augment the core API as described above, the core
system fires a known set of events that plugins can bind to and handle as
they wish. ::

In the most general sense, the events framework is simply a way of binding
arbitrary events with handlers. The events are identified by a unique string
that can be used to bind handlers to them. For example, if the following logic
is executed by your plugin at startup time, ::

    from girder import events

    def handler(event):
        print event.info

    events.bind('some_event', 'my_handler', handler)

And then during runtime the following code executes: ::

    events.trigger('some_event', info='hello')

Then ``hello`` would be printed to the console at that time. More information
can be found in the API documentation for :ref:`events`.

There are a specific set of known events that are fired from the core system.
Plugins should bind to these events at ``load`` time. The semantics of these
events are enumerated below.

*  **Before REST call**
Whenever a REST API route is called, just before executing its default handler,
plugins will have an opportunity to execute code or conditionally override the
default behavior using ``preventDefault`` and ``addResponse``. The identifiers
for these events are of the form, e.g. ``rest.get.item/:id.before``. They
receive the same kwargs as the default route handler in the event's info.

*  **After REST call**
Just like the before REST call event, but this is fired after the default
handler has already executed and returned its value. That return value is
also passed in the event.info for possible alteration by the receiving handler.
The identifier for this event is, e.g. ``rest.get.item/:id.after``. You may
alter the existing return value or override it completely using
``preventDefault`` and ``addResponse`` on the event.

*  **Before model save**
You can receive an event each time a document of a specific resource type is
saved. For example, you can bind to ``model.folder.save`` if you wish to
perform logic each time a folder is saved to the database. You can use
``preventDefault`` on the passed event if you wish for the normal saving logic
not to be performed.

* **Before model deletion**
Triggered each time a model is about to be deleted. You can bind to this via
e.g. ``model.folder.remove`` and optionally ``preventDefault`` on the event.

*  **Override model validation**
You can also override or augment the default ``validate`` methods for a core
model type. Like the normal validation, you should raise a
``ValidationException`` for failure cases, and you can also ``preventDefault``
if you wish for the normal validation procedure not to be executed. The
identifier for these events is, e.g. ``model.user.validate``.

*  **Override user authentication**
If you want to override or augment the normal user authentication process in
your plugin, bind to the ``auth.user.get`` event. If your plugin can
successfully authenticate the user, it should perform the logic it needs and
then ``preventDefault`` on the event and ``addResponse`` containing the
authenticated user document.

*  **On file upload**
This event is always triggered asynchronously and is fired after a file has
been uploaded. The file document that was created is passed in the event info.
You can bind to this event using the identifier ``data.process``.

.. note:: If you anticipate your plugin being used as a dependency by other
   plugins, and want to potentially alert them of your own events, it can
   be worthwhile to trigger your own events from within the plugin. If you do
   that, the identifiers for those events should begin with the name of your
   plugin, e.g. ``events.trigger('cats.something_happened', info='foo')``

Automated testing for plugins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Girder makes it easy to add automated testing to your plugin that integrates
with the main girder testing framework. In general, any CMake code that you
want to be executed for your plugin can be performed by adding a
**plugin.cmake** file in your plugin. ::

    cd plugins/cats ; touch plugin.cmake

That file will be automatically included when girder is configured by CMake.
To add tests for your plugin, you can make use of some handy CMake functions
provided by the core system. For example: ::

    add_python_test(cat PLUGIN cats)
    if(PYTHON_STYLE_TESTS)
      add_python_style_test(pep8_style_cats "${PROJECT_SOURCE_DIR}/plugins/cats/server")
    endif()

Then you should create a ``plugin_tests`` package in your plugin: ::

    mkdir plugin_tests ; cd plugin-tests ; touch __init__.py cat_test.py

The **cat_test.py** file should look like: ::

    from tests import base


    def setUpModule():
        base.enabledPlugins.append('cats')
        base.startServer()


    def tearDownModule():
        base.stopServer()


    class CatsCatTestCase(base.TestCase):

        def testCatsWork(self):
            ...

You can use all of the testing utilities provided by the ``base.TestCase`` class
from core. You will also get coverage results for your plugin aggregated with
the main girder coverage results if coverage is enabled.
