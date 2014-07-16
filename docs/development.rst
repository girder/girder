Developing Girder
=================

Girder is a platform-centric web application whose client and server are very
loosely coupled. As such, development of girder can be divided into the server
(a cherrypy-based python module) and the primary client (a backbone-based) web
client. This section is intended to get prospective contributors to understand
the tools used to develop Girder.

Configuring Your Development Environment
----------------------------------------

In order to develop girder, you can refer to the :doc:`prerequisites` and
:doc:`installation` sections to setup a local development environment. Once
girder is started via ``python -m girder``, the server will reload itself
whenever a python file is modified.

To get the same auto-building behavior for javascript, we use ``grunt-watch``.
Thus, running ``grunt watch`` in the root of the repository will watch for
javascript, stylus, and jade changes in order to rebuild them on-the-fly.

Vagrant
^^^^^^^

A shortcut to going through the installation steps for development is to use
vagrant to setup the environment on a virtualbox virtual machine. To setup this
environment run ``vagrant up`` in the root of the repository. This will spin
up and provision a virtual machine, provided you have vagrant and virtualbox
installed. Once this process is complete, you can run ``vagrant ssh`` in order to
start girder. There is a helper script in the vagrant home directory that will
start girder in a detached screen session. You may want to run a similar process
to run ``grunt watch`` as detailed above.


Utilities
---------

Girder has a set of utility modules and classes that provide handy extractions
for certain functionality. Detailed API documentation can be found :ref:`here <api-docs-utility>`.

Configuration Loading
^^^^^^^^^^^^^^^^^^^^^

The girder configuration loader allows for lazy-loading of configuration values
in a cherrypy-agnostic manner. The recommended idiom for getting the config
object is: ::

    from girder.utility import config
    cur_config = config.getConfig()

There is a configuration file for girder located in **girder/conf**. The file
**girder.dist.cfg** is the file distributed with the repository and containing
the default configuration values. This file shouldn't be edited when deploying
girder. Rather, edit the **girder.local.cfg** file. You only need to edit the
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
utility functions within ``girder.utility.mail_utils``, as in the example below: ::

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
plugin should be prefixed by your plugin name, e.g. "my_plugin.my_template.mako".

.. note:: All emails are sent as rich text (``text/html`` MIME type).


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
and server sides.

A plugin is self-contained in a single directory. To create your plugin, simply
create a directory within the **plugins** directory. In fact, that directory
is the only thing that is truly required to make a plugin in girder. All of the
other components discussed henceforth are optional.

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
change to take effect.

Extending the server-side application
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Within your plugin, you may import packages using relative imports or via
the ``girder.plugins`` package. This will work for your own plugin, but you can
also import modules from any active plugin. You can also import core girder
modules using the ``girder`` package as usual. Example: ::

    from girder.plugins.cats import some_module
    from girder import events

Adding a new route to the web API
*********************************

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

That will make your route automatically appear in the Swagger documentation
and will allow users to interact with it via that UI. See the
:ref:`RESTful API docs<restapi>` for more information about the Swagger page.

If you are creating routes that you explicitly do not wish to be exposed in the
swagger documentation for whatever reason, you can set the handler's description
to ``None``, and then no warning will appear. ::

    myHandler.description = None

Adding a new resource type to the web API
*****************************************

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

Adding a new model type in your plugin
**************************************

Most of the time, if you add a new resource type in your plugin, you'll have a
``Model`` class backing it. These model classes work just like the core model
classes as described in the :ref:`models` section. They must live under the
``server/models`` directory of your plugin, so that they can use the
``ModelImporter`` behavior. If you make a ``Cat`` model in your plugin, you
could access it using ::

    self.model('cat', 'cats')

Where the second argument to ``model`` is the name of your plugin.

The events system
*****************

In addition to being able to augment the core API as described above, the core
system fires a known set of events that plugins can bind to and handle as
they wish.

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
*****************************

Girder makes it easy to add automated testing to your plugin that integrates
with the main girder testing framework. In general, any CMake code that you
want to be executed for your plugin can be performed by adding a
**plugin.cmake** file in your plugin. ::

    cd plugins/cats ; touch plugin.cmake

That file will be automatically included when girder is configured by CMake.
To add tests for your plugin, you can make use of some handy CMake functions
provided by the core system. For example: ::

    add_python_test(cat PLUGIN cats)
    add_python_style_test(pep8_style_cats "${PROJECT_SOURCE_DIR}/plugins/cats/server")

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

Extending the client-side application
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The web client may be extended independently of the server side. Plugins may
import jade templates, stylus files, and javascript files into the application.
The plugin loading system ensures that only content from enabled plugins gets
loaded into the application at runtime.

All of your plugin's extensions to the web client must live in a directory in
the top level of your plugin called **web_client**. ::

    cd plugins/cats ; mkdir web_client

Under the **web_client** directory, there are three optional subdirectories
that can be used to import content:

- ``stylesheets``: Any files ending with **.styl** in this directory or any
  of its subdirectories will be automatically built into CSS and loaded if your
  plugin is enabled. These files must obey
  `Stylus syntax <http://learnboost.github.io/stylus/docs/css-style.html>`_.
  Because these CSS scripts are imported *after* all of the core CSS, any rules
  you write will override any existing core style rules.

- ``templates``: Any files ending with **.jade** in this directory or any of its
  subdirectories will be automatically built as templates available in the
  application. Just like in core, these templates are uniquely identified by
  the name of their file; e.g. ``myTemplate.jade`` could be rendered at runtime
  by calling ``jade.templates.myTemplate()``. So, if you want to override an
  existing core template, simply create one in this directory with the same
  name. If you want to create a template that is not an override of a core
  template, but simply belongs to your plugin, convention dictates that it should
  begin with your plugin name followed by an underscore to avoid collisions, e.g.
  ``cats_catPage.jade``. Documentation for the Jade language can be found
  `here <http://jade-lang.com/reference/>`_.

- ``js``: Any files ending with **.js** in this directory or any of its
  subdirectories will be compiled using uglify and imported into the front-end
  application. The compiled javascript file will be loaded after all of the core
  javascript files are loaded, so it can access all of the objects declared by
  core. The source map for these files will be automatically built and served
  as well.

- ``extra``: Any files in this directory or any of its subdirectories will be
  copied into the **extra** directory under your plugin's built static
  directory. Any additional public static content that is required by your
  plugin that doesn't fall into one of the above categories can be placed here,
  such as static images, fonts, or third-party static libraries.

Javascript extension capabilities
*********************************

Plugins may bind to any of the normal events triggered by core via the
``girder.events`` object. This will accommodate certain events, such as before
and after the application is initially loaded, and when a user logs in or out,
but most of the time plugins will augment the core system using the power of
JavaScript rather than the explicit events framework. One of the most common
use cases for plugins is to execute some code either before or after one of the
core model or view functions is executed. In an object-oriented language, this
would be a simple matter of extending the core class and making a call to the
parent method. The prototypal nature of JavaScript makes that pattern impossible;
instead, we'll use a slightly less straightforward but equally powerful
mechanism. This is best demonstrated by example. Let's say we want to execute
some code any time the core ``HierarchyWidget`` is rendered, for instance to
inject some additional elements into the view. We use the ``girder.wrap``
function to `wrap` the method of the core prototype with our own function. ::

    girder.wrap(girder.views.HierarchyWidget, 'render', function (render) {
        // Call the underlying render function that we are wrapping
        render.call(this);

        // Add a link just below the widget
        this.$('.g-hierarchy-widget').after('<a class="cat-link">Meow</a>');
    });

Notice that instead of simply calling ``render()``, we call ``render.call(this)``.
That is important, as otherwise the value of ``this`` will not be set properly
in the wrapped function.

Now that we've added the link to the core view, we can bind an event handler to
it to make it functional: ::

    girder.views.HierarchyWidget.prototype.events['click a.cat-link'] = function () {
        alert('meow!');
    };

This demonstrates one simple use case for client plugins, but using these same
techniques, you should be able to do almost anything to change the core
application as you need.
