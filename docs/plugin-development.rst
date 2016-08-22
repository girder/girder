.. _plugindevelopment:

Plugin Development
------------------

The capabilities of Girder can be extended via plugins. The plugin framework is
designed to allow Girder to be as flexible as possible, on both the client
and server sides.

A plugin is self-contained in a single directory. To create your plugin, simply
create a directory within the **plugins** directory. In fact, that directory
is the only thing that is truly required to make a plugin in Girder. All of the
other components discussed henceforth are optional.

Example Plugin
^^^^^^^^^^^^^^

We'll use a contrived example to demonstrate the capabilities and components of
a plugin. Our plugin will be called `cats`. ::

    cd plugins ; mkdir cats

The first thing we should do is create a plugin config file in the **cats**
directory. As promised above, this file is not required, but is strongly
recommended by convention. This file contains high-level information about
your plugin, and can be either JSON or YAML. If you want to use YAML features,
make sure to name your config file ``plugin.yml`` instead of ``plugin.json``. For
our example, we'll just use JSON. ::

    touch cats/plugin.json

The plugin config file should specify a human-readable name and description for your
plugin, and can optionally contain a list of other plugins that your plugin
depends on. If your plugin has dependencies, the other plugins will be
enabled whenever your plugin is enabled. The contents of plugin.json for our
example will be:

.. code-block:: json

    {
    "name": "My Cats Plugin",
    "description": "Allows users to manage their cats.",
    "version": "1.0.0",
    "dependencies": ["other_plugin"]
    }

This information will appear in the web client administration console, and
administrators will be able to enable and disable it there. Whenever plugins
are enabled or disabled, a server restart is required in order for the
change to take effect.

Extending the Server-Side Application
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Girder plugins can augment and alter the core functionality of the system in
almost any way imaginable. These changes can be achieved via several mechanisms
which are described below. First, in order to implement the functionality of
your plugin, create a **server** directory within your plugin, and make it
a Python package by creating **__init__.py**. ::

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
also import modules from any active plugin. You can also import core Girder
modules using the ``girder`` package as usual. Example: ::

    from girder.plugins.cats import some_module
    from girder import events

.. _extending-the-api:

Adding a new route to the web API
*********************************

If you want to add a new route to an existing core resource type, just call the
``route()`` function on the existing resource type. For example, to add a
route for ``GET /item/:id/cat`` to the system, ::

    from girder.api import access
    from girder.api.rest import boundHandler

    @access.public
    @boundHandler()
    def myHandler(self, id, params):
        self.requireParams('cat', params)

        return {
           'itemId': id,
           'cat': params['cat']
        }

    def load(info):
        info['apiRoot'].item.route('GET', (':id', 'cat'), myHandler)

You should always add an access decorator to your handler function or method to
indicate who can call the new route.  The decorator is one of ``@access.admin``
(only administrators can call this endpoint), ``@access.user`` (any user who is
logged in can call the endpoint), or ``@access.public`` (any client can call
the endpoint).

In the above example, the :py:obj:`girder.api.rest.boundHandler` decorator is
used to make the unbound method ``myHandler`` behave as though it is a member method
of a :py:class:`girder.api.rest.Resource` instance, which enables convenient access
to methods like ``self.requireParams``.

If you do not add an access decorator, a warning message appears:
``WARNING: No access level specified for route GET item/:id/cat``.  The access
will default to being restricted to administrators.

When you start the server, you may notice a warning message appears:
``WARNING: No description docs present for route GET item/:id/cat``. You
can add self-describing API documentation to your route using the
``describeRoute`` decorator and ``Description`` class as in the following
example: ::

    from girder.api.describe import Description, describeRoute
    from girder.api import access

    @access.public
    @describeRoute(
        Description('Retrieve the cat for a given item.')
        .param('id', 'The item ID', paramType='path')
        .param('cat', 'The cat value.', required=False)
        .errorResponse())
    def myHandler(id, params):
        return {
           'itemId': id,
           'cat': params.get('cat', 'No cat param passed')
        }


That will make your route automatically appear in the Swagger documentation
and will allow users to interact with it via that UI. See the
:ref:`RESTful API docs<restapi>` for more information about the Swagger page.

If you are creating routes that you explicitly do not wish to be exposed in the
Swagger documentation for whatever reason, you can pass ``None`` to the
``describeRoute`` decorator, and no warning will appear. ::

    @describeRoute(None)

Adding a new resource type to the web API
*****************************************

Perhaps for our use case we determine that ``cat`` should be its own resource
type rather than being referenced via the ``item`` resource. If we wish to add
a new resource type entirely, it will look much like one of the core resource
classes, and we can add it to the API in the ``load()`` method. ::

    from girder.api.rest import Resource

    class Cat(Resource):
        def __init__(self):
            super(Cat, self).__init__()
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
for these events are of the form ``rest.get.item/:id.before``. They
receive the same kwargs as the default route handler in the event's info.

Since handlers of this event run prior to the normal access level check of the
underlying route handler, they are bound by the same access level rules as route
handlers; they must be decorated by one of the functions in `girder.api.access`.
If you do not decorate them with one, they will default to requiring administrator
access. This is to prevent accidental reduction of security by plugin developers.
You may change the access level of the route in your handler, but you will
need to do so explicitly by declaring a different decorator than the underlying
route handler.

*  **After REST call**

Just like the before REST call event, but this is fired after the default
handler has already executed and returned its value. That return value is
also passed in the event.info for possible alteration by the receiving handler.
The identifier for this event is, e.g., ``rest.get.item/:id.after``.

You may alter the existing return value, for example adding an additional property ::

    event.info['returnVal']['myProperty'] = 'myPropertyValue'

or override it completely using ``preventDefault`` and ``addResponse`` on the event ::

    event.addResponse(myReplacementResponse)
    event.preventDefault()

*  **Before model save**

You can receive an event each time a document of a specific resource type is
saved. For example, you can bind to ``model.folder.save`` if you wish to
perform logic each time a folder is saved to the database. You can use
``preventDefault`` on the passed event if you wish for the normal saving logic
not to be performed.

* **After model creation**

You can receive an event `after` a resource of a specific type is created and
saved to the database. This is sent immediately before the after-save event,
but only occurs upon creation of a new document. You cannot prevent any default
actions with this hook. The format of the event name is, e.g.
``model.folder.save.created``.

* **After model save**

You can also receive an event `after` a resource of a specific type is saved
to the database. This is useful if your handler needs to know the ``_id`` field
of the document. You cannot prevent any default actions with this hook. The
format of the event name is, e.g. ``model.folder.save.after``.

* **Before model deletion**

Triggered each time a model is about to be deleted. You can bind to this via
e.g., ``model.folder.remove`` and optionally ``preventDefault`` on the event.

* **During model copy**

Some models have a custom copy method (folder uses copyFolder, item uses
copyItem).  When a model is copied, after the initial record is created, but
before associated models are copied, a copy.prepare event is sent, e.g.
``model.folder.copy.prepare``.  The event handler is passed a tuple of
``((original model document), (copied model document))``.  If the copied model
is altered, the handler should save it without triggering events.

When the copy is fully complete, and copy.after event is sent, e.g.
``model.folder.copy.after``.

*  **Override model validation**

You can also override or augment the default ``validate`` methods for a core
model type. Like the normal validation, you should raise a
``ValidationException`` for failure cases, and you can also ``preventDefault``
if you wish for the normal validation procedure not to be executed. The
identifier for these events is, e.g., ``model.user.validate``.

*  **Override user authentication**

If you want to override or augment the normal user authentication process in
your plugin, bind to the ``auth.user.get`` event. If your plugin can
successfully authenticate the user, it should perform the logic it needs and
then ``preventDefault`` on the event and ``addResponse`` containing the
authenticated user document.

*  **Before file upload**

This event is triggered as an upload is being initialized.  The event
``model.upload.assetstore`` is sent before the ``model.upload.save`` event.
The event information is a dictionary containing ``model`` and ``resource``
with the resource model type and resource document of the upload parent.  For
new uploads, the model type will be either ``item`` or ``folder``.  When the
contents of a file are being replaced, this will be a ``file``.  To change from
the current assetstore, add an ``assetstore`` key to the event information
dictionary that contains an assetstore model document.

*  **Just before a file upload completes**

The event ``model.upload.finalize`` after the upload is completed but before
the new file is saved.  This can be used if the file needs to be altered or the
upload should be cancelled at the last moment.

*  **On file upload**

This event is always triggered asynchronously and is fired after a file has
been uploaded. The file document that was created is passed in the event info.
You can bind to this event using the identifier ``data.process``.

.. note:: If you anticipate your plugin being used as a dependency by other
   plugins, and want to potentially alert them of your own events, it can
   be worthwhile to trigger your own events from within the plugin. If you do
   that, the identifiers for those events should begin with the name of your
   plugin, e.g., ``events.trigger('cats.something_happened', info='foo')``

Automated testing for plugins
*****************************

Girder makes it easy to add automated testing to your plugin that integrates
with the main Girder testing framework. In general, any CMake code that you
want to be executed for your plugin can be performed by adding a
**plugin.cmake** file in your plugin. ::

    cd plugins/cats ; touch plugin.cmake

That file will be automatically included when Girder is configured by CMake.
To add tests for your plugin, you can make use of some handy CMake functions
provided by the core system. For example:

.. code-block:: cmake

    add_python_test(cat PLUGIN cats)
    add_python_style_test(python_static_analysis_cats "${PROJECT_SOURCE_DIR}/plugins/cats/server")

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
the main Girder coverage results if coverage is enabled.

Plugins can also use the external data interface provided by Girder as described
in :ref:`use_external_data`.  For plugins, the data key files should be placed
inside a directory called ``plugin_tests/data/``.  When referencing the
files, they must be prefixed by your plugin name as follows

.. code-block:: cmake

    add_python_test(my_test EXTERNAL_DATA plugins/cats/test_file.txt)

Then inside your unittest, the file will be available under the main data path
as ``os.environ['GIRDER_TEST_DATA_PREFIX'] + '/plugins/cats/test_file.txt'``.

Extending the Client-Side Application
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The web client may be extended independently of the server side. Plugins may
import Jade templates, Stylus files, and JavaScript files into the application.
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
  the name of their file; e.g., ``myTemplate.jade`` could be rendered at runtime
  by calling ``girder.templates.myTemplate()``. So, if you want to override an
  existing core template, simply create one in this directory with the same
  name. If you want to create a template that is not an override of a core
  template, but simply belongs to your plugin, convention dictates that it should
  begin with your plugin name followed by an underscore to avoid collisions, e.g.,
  ``cats_catPage.jade``. Documentation for the Jade language can be found
  `here <http://jade-lang.com/reference/>`_.

- ``js``: Any files ending with **.js** in this directory or any of its
  subdirectories will be compiled using uglify and imported into the front-end
  application. The compiled JavaScript file will be loaded after all of the core
  JavaScript files are loaded, so it can access all of the objects declared by
  core. The source map for these files will be automatically built and served
  as well.

- ``extra``: Any files in this directory or any of its subdirectories will be
  copied into the **extra** directory under your plugin's built static
  directory. Any additional public static content that is required by your
  plugin that doesn't fall into one of the above categories can be placed here,
  such as static images, fonts, or third-party static libraries.

Linting and Style Checking Client-Side Code
*******************************************

Girder uses `ESLint <http://eslint.org/>`_ to perform static analysis of its
own JavaScript files.  Developers can easily add the same static analysis
tests to their own plugins using a CMake function call defined by Girder.

.. code-block:: cmake

    add_eslint_test(
        js_static_analysis_cats "${PROJECT_SOURCE_DIR}/plugins/cats/web_client"
    )

This will check all files with the extension **.js** inside of the ``cats`` plugin's
``web_client`` directory using the same style rules enforced within Girder itself.
Plugin developers can also choose to extend or even override entirely the core style
rules.  To do this, you only need to provide a path to a custom ESLint configuration
file as follows.

.. code-block:: cmake

    add_eslint_test(
        js_static_analysis_cats "${PROJECT_SOURCE_DIR}/plugins/cats/web_client"
        ESLINT_CONFIG_FILE "${PROJECT_SOURCE_DIR}/plugins/cats/.eslintrc"
    )

You can `configure ESLint <http://eslint.org/docs/user-guide/configuring.html>`_
inside this file however you choose.  For example, to extend Girder's own
configuration by adding a new global variable ``cats`` and you really hate using
semicolons, you can put the following in your **.eslintrc**

.. code-block:: javascript

    {
        "extends": "../../.eslintrc",
        "globals": {
            "cats": true
        },
        "rules": {
            "semi": 0
        }
    }

Installing custom dependencies from npm
***************************************

There are two types of node dependencies you may need to install for your plugin.
Each type needs to be installed differently due to how node manages external packages.

- Run time dependencies that your application relies on may be handled in one
  of two ways. If you are writing a simple plugin that does not contain its own
  Gruntfile, these dependencies should be installed into Girder's own
  **node_modules** directory by specifying them in the ``npm.dependencies``
  section of your ``plugin.json`` file.

  .. code-block:: json

      {
          "name": "MY_PLUGIN",
          "npm": {
              "dependencies": {
                  "vega": "^2.6.0"
              }
          }
      }

  If instead you are using a custom Grunt build with a Gruntfile, the
  dependencies should be installed into your plugin's **node_modules** directory
  by providing a `package.json <https://docs.npmjs.com/files/package.json>`_
  file just as they are used for standalone node applications.  When such a file
  exists in your plugin directory, ``npm install`` will be executed in a new
  process from within your package's directory.

- Build time dependencies that your Grunt tasks rely on to assemble the sources
  for deployment need to be installed into Girder's own **node_modules** directory.
  These dependencies will typically be Grunt extensions defining extra tasks used
  by your build.  Such dependencies should be listed under ``grunt.dependencies``
  as an object (much like dependencies in **package.json**) inside your
  **plugin.json** or **plugin.yml** file.

  .. code-block:: json

      {
          "name": "MY_PLUGIN",
          "grunt": {
              "dependencies": {
                  "grunt-shell": ">=0.2.1"
              }
          }
      }

  In addition to installing these dependencies, Girder will also load grunt extensions
  contained in them before executing any tasks.

.. note:: Packages installed into Girder's scope can possibly overwrite an alternate
          version of the same package.  Care should be taken to only list packages here
          that are not already provided by Girder's own build time dependencies.

Executing custom Grunt build steps for your plugin
**************************************************

For more complex plugins which require custom Grunt tasks to build, the user can
specify custom targets within their own Grunt file that will be executed when
the main Girder Grunt step is executed. To use this functionality, add a **grunt**
key to your **plugin.json** file.

.. code-block:: json

    {
    "name": "MY_PLUGIN",
    "grunt":
        {
        "file" : "Gruntfile.js",
        "defaultTargets": [ "MY_PLUGIN_TASK" ],
        "autobuild": true
        }
    }

This will allow to register a Gruntfile relative to the plugin root directory
and add any target to the default one using the "defaultTargets" array.

.. note:: The **file** key within the **grunt** object must be a path that is
   relative to the root directory of your plugin. It does not have to be called
   ``Gruntfile.js``, it can be called anything you want.

.. note:: Girder creates a number of Grunt build tasks that expect plugins to be
   organized according to a certain convention.  To opt out of these tasks, add
   an **autobuild** key (default: **true**) within the **grunt** object and set
   it to **false**.

All paths within your custom Grunt tasks must be relative to the root directory
of the Girder source repository, rather than relative to the plugin directory.

.. code-block:: javascript

    module.exports = function (grunt) {
        grunt.registerTask('MY_PLUGIN_TASK', 'Custom plugin build task', function () {
            /* ... Execute custom behavior ... */
        });
    };

JavaScript extension capabilities
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
function to `wrap` the method of the core prototype with our own function.

.. code-block:: javascript

    girder.wrap(girder.views.HierarchyWidget, 'render', function (render) {
        // Call the underlying render function that we are wrapping
        render.call(this);

        // Add a link just below the widget
        this.$('.g-hierarchy-widget').after('<a class="cat-link">Meow</a>');
    });

Notice that instead of simply calling ``render()``, we call ``render.call(this)``.
That is important, as otherwise the value of ``this`` will not be set properly
in the wrapped function.

Now that we have added the link to the core view, we can bind an event handler to
it to make it functional:

.. code-block:: javascript

    girder.views.HierarchyWidget.prototype.events['click a.cat-link'] = function () {
        alert('meow!');
    };

This demonstrates one simple use case for client plugins, but using these same
techniques, you should be able to do almost anything to change the core
application as you need.

Setting an empty layout for a route
***********************************

If you have a route in your plugin that you would like to have an empty layout,
meaning that the Girder header, nav bar, and footer are hidden and the Girder body is
evenly padded and displayed, you can specify an empty layout in the ``navigateTo``
event trigger.

As an example, say your plugin wanted a ``frontPage`` route for a Collection which
would display the Collection with only the Girder body shown, you could add the following
route to your plugin.

.. code-block:: javascript

    girder.router.route('collection/:id/frontPage', 'collectionFrontPage', function (collectionId, params) {
        var collection = new girder.models.CollectionModel();
        collection.set({
            _id: collectionId
        }).on('g:fetched', function () {
            girder.events.trigger('g:navigateTo', girder.views.CollectionView, _.extend({
                collection: collection
            }, params || {}), {layout: girder.Layout.EMPTY});
        }, this).on('g:error', function () {
            girder.router.navigate('/collections', {trigger: true});
        }, this).fetch();
    });
