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

The plugin config file should specify a human-readable name and description for
your plugin. It can also optionally contain a URL to documentation and
a list of other plugins that your plugin depends on. If your plugin has
dependencies, the other plugins will be enabled whenever your plugin is enabled.
The contents of plugin.json for our example will be:

.. note:: If you have both ``plugin.json`` and ``plugin.yml`` files in the directory, the
   ``plugin.json`` will take precedence.

.. code-block:: json

    {
        "name": "My Cats Plugin",
        "description": "Allows users to manage their cats.",
        "url": "http://girder.readthedocs.io/en/latest/plugin/mycat.html",
        "version": "1.0.0",
        "dependencies": ["other_plugin"]
    }

.. note:: Some plugins depend on other plugins, but only for building web client code, not
    at runtime. For these cases, rather than the ``dependencies`` field, use the
    ``staticWebDependencies`` field instead. This will allow the plugin to import web
    code from the other plugin, but will not require the other plugin to be built or enabled
    at runtime.

This information will appear in the web client administration console, and
administrators will be able to enable and disable it there. Whenever plugins
are enabled or disabled, a server restart is required in order for the
change to take effect.

If you are developing a plugin for girder, sometimes using the Rebuild and restart button
on the Plugins page may be undesirable as it will rebuild core and all enabled plugins
in production mode, which will take some time and doesn't provide sourcemaps.
Rebuild specific plugin restart the server may be a better choice. See `During Development <development.html#during-development>`__ for details.



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
route for ``GET /item/:id/cat`` to the system,

.. code-block:: python

    from girder.api import access
    from girder.api.rest import boundHandler

    @access.public
    @boundHandler
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
``autoDescribeRoute`` decorator and :py:class:`girder.api.describe.Description` class as in the following
example:

.. code-block:: python

    from girder.api.describe import Description, autoDescribeRoute
    from girder.api import access

    @access.public
    @autoDescribeRoute(
        Description('Retrieve the cat for a given item.')
        .param('id', 'The item ID', paramType='path')
        .param('cat', 'The cat value.', required=False)
        .errorResponse())
    def myHandler(id, cat):
        return {
           'itemId': id,
           'cat': cat
        }

That will make your route automatically appear in the Swagger documentation
and will allow users to interact with it via that UI. See the
:ref:`RESTful API docs<restapi>` for more information about the Swagger page.
In addition, the ``autoDescribeRoute`` decorator handles a lot of the validation
and type coercion for you, with the benefit of ensuring that the documentation of
the endpoint inputs matches their actual behavior. Documented parameters will be
sent to the method as kwargs (so the order you declare them in the header doesn't matter).
Any additional parameters that were passed but not listed in the ``Description`` object
will be contained in the ``params`` kwarg as a dictionary, if that parameter is present. The
validation of required parameters, coercion to the correct data type, and setting default
values is all handled automatically for you based on the parameter descriptions in the
``Description`` object passed. Two special methods of the ``Description`` object can be used for
additional behavior control: :py:func:`girder.api.describe.Description.modelParam` and
:py:func:`girder.api.describe.Description.jsonParam`.

The ``modelParam`` method is used to convert parameters passed in as IDs to the model document
corresponding to those IDs, and also can perform access checks to ensure that the user calling the
endpoint has the requisite access level on the resource. For example, we can convert the above
handler to use it:

.. code-block:: python

    @access.public
    @autoDescribeRoute(
        Description('Retrieve the cat for a given item.')
        .modelParam('id', 'The item ID', model='item', level=AccessType.READ)
        .param('cat', 'The cat value.', required=False)
        .errorResponse())
    def myHandler(item, cat, params):
        return {
           'item': item,
           'cat': cat
        }

The ``jsonParam`` method can be used to indicate that a parameter should be parsed as
a JSON string into the corresponding python value and passed as such.

If you are creating routes that you explicitly do not wish to be exposed in the
Swagger documentation for whatever reason, you can pass ``hide=True`` to the
``autoDescribeRoute`` decorator, and no warning will appear.

.. code-block:: python

    @autoDescribeRoute(Description(...), hide=True)

Adding a new resource type to the web API
*****************************************

Perhaps for our use case we determine that ``cat`` should be its own resource
type rather than being referenced via the ``item`` resource. If we wish to add
a new resource type entirely, it will look much like one of the core resource
classes, and we can add it to the API in the ``load()`` method.

.. code-block:: python

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

Adding a prefix to an API
*************************

It is possible to provide a prefix to your API, allowing associated endpoints to
be grouped together. This is done by creating a prefix when mounting the resource.
Note that ``resourceName`` is **not** provided as the resource name is also derived
from the mount location.


.. code-block:: python

    from girder.api.rest import Resource, Prefix

    class Cat(Resource):
        def __init__(self):
            super(Cat, self).__init__()

            self.route('GET', (), self.findCat)
            self.route('GET', (':id',), self.getCat)
            self.route('POST', (), self.createCat)
            self.route('PUT', (':id',), self.updateCat)
            self.route('DELETE', (':id',), self.deleteCat)

        def getCat(self, id, params):
            ...

    def load(info):
        info['apiRoot'].meow = Prefix()
        info['apiRoot'].meow.cat = Cat()

The endpoints are now mounted at meow/cat/


Adding a new model type in your plugin
**************************************

Most of the time, if you add a new resource type in your plugin, you'll have a
``Model`` class backing it. These model classes work just like the core model
classes as described in the :ref:`models` section.

Adding custom access flags
**************************

Girder core provides a way to assign a permission level (read, write, and own) to data in the
hierarchy to individual users or groups. In addition to this level, users and groups can also
be granted special access flags on resources in the hierarchy. If you want to expose a new
access flag on data, have your plugin globally register the flag in the system:

.. code-block:: python

    from girder.constants import registerAccessFlag

    registerAccessFlag(key='cats.feed', name='Feed cats', description='Allows users to feed cats')

When your plugin is enabled, a new checkbox will automatically appear in the access control
dialog allowing resource owners to specify what users and groups are allowed to feed
cats (assuming cats are represented by data in the hierarchy). Additionally, if your resource is
public, you will also be able to configure which access flags are available to the public.
If your plugin exposes another endpoint, say ``POST cat/{id}/food``, inside that route handler, you
can call ``requireAccessFlags``, e.g.:

.. code-block:: python

    from girder.plugins.cats.models.cat import Cat

    @access.user
    @autoDescribeRoute(
        Description('Feed a cat')
        .modelParam('id', 'ID of the cat', model=Cat, level=AccessType.WRITE)
    )
    def feedCats(self, cat, params):
        Cat().requireAccessFlags(item, user=getCurrentUser(), flags='cats.feed')

        # Feed the cats ...

That will throw an ``AccessException`` if the user does not possess the specified access
flag(s) on the given resource. You can equivalently use the ``Description.modelParam``
method using ``autoDescribeRoute``, passing a ``requiredFlags`` parameter, e.g.:

.. code-block:: python

    @access.user
    @autoDescribeRoute(
        Description('Feed a cat')
        .modelParam('id', 'ID of the cat', model='cat', plugin='cats', level=AccessType.WRITE,
                    requiredFlags='cats.feed')
    )
    def feedCats(self, cat, params):
        # Feed the cats ...

Normally, anyone with ownership access on the resource will be allowed to enable the flag on
their resources. If instead you want to make it so that only site administrators can enable your
custom access flag, pass ``admin=True`` when registering the flag, e.g.

.. code-block:: python

    registerAccessFlag(key='cats.feed', name='Feed cats', admin=True)

We cannot prescribe exactly how access flags should be used; Girder core does not
expose any on its own, and the sorts of policies that they will enforce will be entirely
defined by the logic of your plugin.

The events system
*****************

In addition to being able to augment the core API as described above, the core
system fires a known set of events that plugins can bind to and handle as
they wish.

In the most general sense, the events framework is simply a way of binding
arbitrary events with handlers. The events are identified by a unique string
that can be used to bind handlers to them. For example, if the following logic
is executed by your plugin at startup time,

.. code-block:: python

    from girder import events

    def handler(event):
        print event.info

    events.bind('some_event', 'my_handler', handler)

And then during runtime the following code executes:

.. code-block:: python

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

*  **Before file move**

The event ``model.upload.movefile`` is triggered when a file is about to be
moved from one assetstore to another.  The event information is a dictionary
containing ``file`` and ``assetstore`` with the current file document and the
target assetstore document.  If ``preventDefault`` is called, the move will be
cancelled.

.. note:: If you anticipate your plugin being used as a dependency by other
   plugins, and want to potentially alert them of your own events, it can
   be worthwhile to trigger your own events from within the plugin. If you do
   that, the identifiers for those events should begin with the name of your
   plugin, e.g., ``events.trigger('cats.something_happened', info='foo')``

* **User login**

The event ``model.user.authenticate`` is fired when a user is attempting to
login via a username and password. This allows alternative authentication
modes to be used instead of core, or prior to attempting core authentication.
The event info contains two keys, "login" and "password".

.. _client-side-plugins:

Extending the Client-Side Application
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The web client may be extended independently of the server side. Plugins may
import Pug templates, Stylus files, and JavaScript files into the application.
The plugin loading system ensures that only content from enabled plugins gets
loaded into the application at runtime.

By default, all of your plugin's extensions to the web client must live in a directory in
the top level of your plugin called **web_client**. ::

    cd plugins/cats ; mkdir web_client

Under the **web_client** directory, you must have a webpack entry point file called **main.js**.
In this file, you can import code from your plugin using relative paths, or relative to the special alias
**girder_plugins/<your_plugin_key>**. For example,
``import template from 'girder_plugins/cats/templates/myTemplate.pug`` would import the template file
located at ``plugins/cats/web_client/templates/myTemplate.pug``. Core Girder code can be imported
relative to the path **girder**, for example ``import View from 'girder/views/View';``. The entry
point defined in your **main.js** file will be automatically built once the plugin has been enabled,
and your built code will be served with the application once the server has been restarted.

You can also customize which file is used as the webpack entry point, using a
``webpack`` section in your plugin config. The ``main`` property is a path relative
to your plugin directory naming the entry point file (by default, as discussed
above, the value of this property is ``web_client/main.js``):

.. code-block:: json

    {
        "name": "MY_PLUGIN",
        "webpack": {
            "main": "web_external/index.js"
        }
    }

You may also set ``main`` to an object that maps bundle names to entry points, which is
helpful for plugins that want to build multiple targets using the same loaders. For example:

.. code-block:: json

    {
        "name": "MY_PLUGIN",
        "webpack": {
            "main": {
                "plugin": "web_client/main.js",
                "external": "web_external/main.js"
            }
        }
    }

That will cause both ``plugin.min.*`` and ``external.min.*`` files to appear in the
built directory. The file paths of the entry points should be specified relative to the
plugin directory.


.. _webpackhelper:

Customizing the Webpack Build
*****************************

Girder's core webpack configuration may not be quite right for your plugin. The
plugin config's ``webpack`` section may contain a ``configHelper`` property (default
value: ``webpack.helper.js``) that names a relative path to a JavaScript file that
exports a "webpack helper". This helper is simply a function of two arguments -
Girder's core webpack configuration object, and a hash of useful data about the
plugin build - that returns a modified webpack configuration to use to build the
plugin. This can be useful if you wish to use custom webpack loaders or plugins
to build your plugin.

The object passed to the helper function contains the following keys:

- ``plugin``: the name of the plugin
- ``output``: the name of the output bundle, which is "plugin" by default.
- ``main``: the full path to the entry point file for the bundle.
- ``pluginEntry``: the webpack entry point for the plugin (e.g.
  ``plugins/MY_PLUGIN/plugin``)
- ``pluginDir``: the full path to the plugin directory
- ``nodeDir``: the full path to the plugin's dedicated NPM dependencies

Additionally, you can instruct the build system to start with an empty loader
list. You may want to do this to ensure that your plugin files are processed by
webpack exactly as you see fit, and not risk any of Girder's predefined loaders
getting involved where you may not expect them. To use this option, set the
``webpack.defaultLoaders`` property to ``false`` (the property is ``true`` by
default):

.. code-block:: json

    {
        "name": "MY_PLUGIN",
        "webpack": {
            "configHelper": "plugin_webpack.js",
            "defaultLoaders": false
        }
    }

Installing custom dependencies from npm
***************************************

If your application requires third-party npm packages to be installed, there are a few ways to achieve this. The
first is to declare them in your ``plugin.json`` file under ``npm.dependencies``:

  .. code-block:: json

      {
          "name": "MY_PLUGIN",
          "npm": {
              "dependencies": {
                  "vega": "^2.6.0"
              }
          }
      }

You can also name a JSON file containing NPM dependencies, as follows:

  .. code-block:: json

      {
          "name": "MY_PLUGIN",
          "npm": {
              "file": "package.json",
              "fields": ["devDependencies"],
              "localNodeModules": true
          }
      }

The ``npm.file`` property is a path to a JSON file relative to the plugin
directory (``package.json`` is a convenient choice, simply because the ``npm
install --save-dev`` command manipulates this file by default), while
``npm.fields`` specifies which top-level keys in that file contain package names
to install (by default, this property has the value ``['devDependencies',
'dependencies', 'optionalDependencies']``). If the ``localNodeModules`` option
is set to ``true``, then the dependencies will be installed within a separate
directory so that they will not collide with Girder's own set of node_modules.

The final alternative for Webpack-built plugins is to set the ``npm.install``
configuration property to ``true``; this will cause the build system to run
``npm install`` in the plugin directory.

When you use the `import` directive within your plugin code, for example:

.. code-block:: javascript

    import foobar from 'foobar';

The build process will search for the ``'foobar'`` module in the following locations, in order:

1. The plugin's local modules directory that is created if ``npm.localNodeModules`` has
   been set to ``true`` in the plugin configuration file.
2. The ``node_modules`` directory underneath the plugin directory, which would exist when using
   ``npm.install: true``, or if node modules had been installed there manually.
3. Within Girder's own ``node_modules`` directory.

.. note:: One notable exception to this rule is for the jQuery library; having multiple versions of jQuery from
          different targets often breaks things at runtime, so plugins will always use the same jQuery
          as Girder core.

If for some reason you need to modify this search order for your plugin, you can do so via the ``webpack.helper.js``
file documented in the :ref:`webpackhelper` section. To do so, you can override the ``resolve.modules`` field of
the configuration and set it to a list of paths to search in order. If you need to modify the path to search for
webpack loaders instead of module imports, use the ``resolveLoader.modules`` list instead.

Controlling the Build Output
****************************

In the plugin config's ``webpack`` section, you can set the ``webpack.output``
property to control the name of the plugin bundle file. By default this value is
``plugin``, so that the resulting file will be
``clients/web/static/build/plugins/MY_PLUGIN/plugin.min.js``. Girder automatically
detects such files named ``plugin.min.js`` and automatically loads them into the
main web client.

To create an "external" plugin, simply change the output name to any other
value. One reasonable choice is ``index``. These plugins can be used to create
wholly independent web clients that don't explicitly depend on the core Girder
client being loaded.

.. note:: If you use an object to specify an output to entry point mapping in ``webpack.main``,
          the ``webpack.output`` value will be ignored if specified.

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

Plugins may bind to any of the normal events triggered by core via a global
events object that can be imported like so:

.. code-block:: javascript

    import events from 'girder/events';

    ...

    this.listenTo(events, 'g:event_name', () => { do.something(); });

This will accommodate certain events, such as before
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
inject some additional elements into the view. We use Girder's ``wrap`` utility
function to `wrap` the method of the core prototype with our own function.

.. code-block:: javascript

    import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
    import { wrap } from 'girder/utilities/PluginUtils';

    // Import our template file from our plugin using a relative path
    import myTemplate from './templates/hierachyWidgetExtension.pug';

    // CSS files pertaining to this view should be imported as a side-effect
    import './stylesheets/hierarchyWidgetExtension.styl';

    wrap(HierarchyWidget, 'render', function (render) {
        // Call the underlying render function that we are wrapping
        render.call(this);

        // Add a link just below the widget using our custom template
        this.$('.g-hierarchy-widget').after(myTemplate());
    });

Notice that instead of simply calling ``render()``, we call ``render.call(this)``.
That is important, as otherwise the value of ``this`` will not be set properly
in the wrapped function.

Now that we have added the link to the core view, we can bind an event handler to
it to make it functional:

.. code-block:: javascript

    HierarchyWidget.prototype.events['click a.cat-link'] = () => {
        alert('meow!');
    };

This demonstrates one simple use case for client plugins, but using these same
techniques, you should be able to do almost anything to change the core
application as you need.

JavaScript events
*****************

The JavaScript client handles notifications from the server and Backbone events
in client-specific code.  The server notifications originate on the server and
can be monitored by both the server's Python code and the client's JavaScript
code.  The client Backbone events are solely within the web client, and do not
get transmitted to the server.

If the connection to the server is interrupted, the client will not receive
server events.  Periodically, the client will attempt to reconnect to the
server to resume handling events.  Similarly, if client's browser tab is placed
in the background for a long enough period of time, the connection that listens
for server events will be stopped to prevent excessive resource use.  When the
browser's tab regains focus, the client will once again receive server events.

When the connection to the server's event stream is interrupted, a
``g:eventStream.stop`` Backbone event is triggered on the ``EventStream``
object.  When the server is once more sending events, it first sends a
``g:eventStream.start`` event.  Clients can listen to these events and refresh
necessary components to ensure that data is current.

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

    import events from 'girder/events';
    import router from 'girder/router';
    import { Layout } from 'girder/constants';
    import CollectionModel from 'girder/models/CollectionModel';
    import CollectionView from 'girder/views/body/CollectionView';

    router.route('collection/:id/frontPage', 'collectionFrontPage', function (collectionId, params) {
        var collection = new CollectionModel();
        collection.set({
            _id: collectionId
        }).on('g:fetched', function () {
            events.trigger('g:navigateTo', CollectionView, _.extend({
                collection: collection
            }, params || {}), {layout: Layout.EMPTY});
        }, this).on('g:error', function () {
            router.navigate('/collections', {trigger: true});
        }, this).fetch();
    });

Automated testing for plugins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Girder makes it easy to add automated testing to your plugin that integrates with the main Girder
testing framework. In general, any CMake code for configuring testing can be added to the
``plugin.cmake`` file in your plugin. For example:

.. code-block:: bash

    cd plugins/cats ; touch plugin.cmake

That file will be automatically included when Girder is configured by CMake. To add tests for your
plugin, you can make use of a handy CMake function provided by the core system. Simply add to your
``plugin.cmake``:

.. code-block:: cmake

    add_standard_plugin_tests()

This will automatically run static analysis tools on most parts of your plugin, including the
server, client, and testing files. Additionally, it will detect and run any tests in the special
``plugin_tests`` directory of your plugin, provided that server-side tests are named with the suffix
``_test.py`` (and the directory contains a ``__init__.py`` to make it a Python module) and
client-side tests are named with the suffix ``Spec.js``. For example:

.. code-block:: bash

    cd plugins/cats; mkdir plugin_tests ; cd plugin_tests ; touch __init__.py cat_test.py catSpec.js

For more sophisticated configuration of plugin testing, options to ``add_standard_plugin_tests`` can
be used to disable some of the automatically-added tests, so they can be explicitly added with
additional options. See the ``add_standard_plugin_tests`` implementation for full option
documentation.

Testing Server-Side Code
************************

.. note:: Support for ``pytest`` tests has not yet been added to plugins.

The ``plugin_tests/cat_test.py`` file should look like:

.. code-block:: python

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

.. note:: When enabling coverage in a plugin, only files residing under the plugin's
          ``server`` directory will be included.  See :ref:`python-coverage-paths`
          to change the paths used to generate python coverage reports.

Testing Client-Side Code
************************

Web client components may also be tested, using the
`Jasmine 1.3 test framework <https://jasmine.github.io/1.3/introduction>`_.

At the start of a plugin client test file, the built plugin files must be explicitly loaded,
typically with the ``girderTest.importPlugin`` function.

.. note:: Plugin dependency resolution will not take place when loading built plugin files in the
          test environment. If your plugin has dependencies on other Girder plugins, you should
          make multiple calls to ``girderTest.importPlugin``, loading any dependant plugins in
          topologically sorted order, before loading your plugin with ``girderTest.importPlugin``
          last.

If the plugin test requires an instance of the Girder client app to be running, it can be
started with ``girderTest.startApp()`` immediately after plugins are imported. Plugin tests that
perform only unit tests or standalone instantiation of views may be able to skip starting the Girder
client app.

Jasmine specs (defined with ``it``) are not run until the plugin (and app, if started) are fully
loaded, so they should be defined directly inside a suite (defined with ``describe``) at the
top-level.

For example, the cats plugin would define tests in a ``plugin_tests/catSpec.js`` file, like:

.. code-block:: javascript

    girderTest.importPlugin('cats');
    girderTest.startApp();

    describe("Test the cats plugin", function() {
        it("tests some new functionality", function() {
            ...
        });
    });


Using External Data Artifacts
*****************************

Plugin tests can also use the external data artifact interface provided by Girder as described in
:ref:`use_external_data`.  The artifact key files should be placed inside a directory
called ``plugin_tests/data/``.  Tests which depend on these artifacts should be explicitly added
using the ``EXTERNAL_DATA`` option, with arguments of data artifact names (without the hash file
extension) prefixed by ``plugins/<plugin_name>``. For example:

.. code-block:: cmake

    add_standard_plugin_tests(NO_SERVER_TESTS)
    add_python_test(cats_server_test PLUGIN cats EXTERNAL_DATA plugins/cats/test_file.txt)

Then, within your test environment, the artifact will be available
under the a location specified by the ``GIRDER_TEST_DATA_PREFIX`` environment variable, in the
subdirectory ``plugins/<plugin_name>``. For example, in the same ``cats_server_test``, the artifact
file can be loaded at the path:

.. code-block:: python

    os.path.join(os.environ['GIRDER_TEST_DATA_PREFIX'], 'plugins', 'cats', 'test_file.txt')


Customizing Static Analysis of Client-Side Code
***********************************************

Girder uses `ESLint <http://eslint.org/>`_ to perform static analysis of its own JavaScript files.
If the ``add_standard_plugin_tests`` CMake macro is used, these same tests are run on all
Javascript code in the ``web_client`` and ``plugin_tests`` directories of a plugin.

However, plugin developers can also choose to extend or even entirely override the core style rules.
To do this, you only need to provide a path to a custom ESLint configuration file, using the
``ESLINT_CONFIG_FILE`` option to ``add_eslint_test``. Of course, since ``add_standard_plugin_tests``
should be prevented from adding these tests, static analysis should also be manually added to PugJS
template files with ``add_puglint_test`` and ``add_stylint_test``. For example:

.. code-block:: cmake

    add_standard_plugin_tests(NO_CLIENT)
    add_eslint_test(js_static_analysis_cats "${PROJECT_SOURCE_DIR}/plugins/cats/web_client"
        ESLINT_CONFIG_FILE "${PROJECT_SOURCE_DIR}/plugins/cats/.eslintrc.json")
    add_puglint_test(cats "${PROJECT_SOURCE_DIR}/plugins/cats/web_client/templates")
    add_stylint_test(cats "${PROJECT_SOURCE_DIR}/plugins/cats/web_client/stylesheets")

You can `configure ESLint <http://eslint.org/docs/user-guide/configuring.html>`_ inside your
``.eslintrc.json`` file however you choose.  For example, to extend Girder's own configuration to
add a new global variable ``cats`` and stop requiring semicolons to terminate statements, you can
put the following in your ``.eslintrc.json``:

.. code-block:: javascript

    {
        "extends": "../../.eslintrc.json",
        "globals": {
            "cats": true
        },
        "rules": {
            "semi": 0
        }
    }
