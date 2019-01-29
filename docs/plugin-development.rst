.. _plugindevelopment:

Plugin Development
------------------

The capabilities of Girder can be extended via plugins. The plugin framework is
designed to allow Girder to be as flexible as possible, on both the client
and server sides.

A plugin is self-contained python package with an optional "web_client" directory
containing the client side extension.  In this document, we describe the minimal
components necessary to create and distribute a python package containing a Girder
plugin for basic use cases.  For a more detailed guide, see python's own
`packaging documentation <https://packaging.python.org/guides/distributing-packages-using-setuptools/>`_
and `tutorial <https://python-packaging.readthedocs.io/en/latest/index.html>`_.

Quick Start
^^^^^^^^^^^

We maintain a `Cookiecutter template <https://github.com/girder/cookiecutter-girder-plugin>`_
to help developers get started with their own Girder plugin.  To generate your own plugin
using this template, install the cookiecutter package ::

    pip install cookiecutter

and run this command ::

    cookiecutter gh:girder/cookiecutter-girder-plugin

It will ask you a few questions to customize the plugin.  For details on these options
see the `README <https://github.com/girder/cookiecutter-girder-plugin/blob/master/README.md>`_
in the template's git repository.

Example Plugin
^^^^^^^^^^^^^^

We'll use a contrived example to demonstrate the capabilities and components of
a plugin. Our plugin will be called `cats`. ::

    mkdir cats

The first thing we should do is create a ``setup.py`` file describing the
package we are going to create.

.. code-block:: python

  from setuptools import setup, find_packages

  setup(
      name='girder_cats',
      version='1.0.0',
      description='A contrived example of a Girder plugin.',
      author='Plugin Development, Inc.',
      author_email='plugin-developer@email.com',
      url='https://my-plugin-documentation-page.com/cats',
      license='Apache 2.0',
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'License :: OSI Approved :: Apache Software License'
      ],
      include_package_data=True,
      packages=find_packages(exclude=['plugin_tests']),
      zip_safe=False,
      setup_requires=['setuptools-git'],
      install_requires=['girder>=3', 'girder-jobs'],
      entry_points={
          'girder.plugin': [ 'cats = girder_cats.CatsPlugin' ]
      }
  )

Many of these values are metadata associated with a standard python package.  See also
the list of `available classifiers <https://pypi.org/pypi?%3Aaction=list_classifiers>`_
that can be added to aid in discoverability of your package.  Several arguments
in this example are specific to a Girder plugin.  These are as follows:

``include_package_data=True``
    This tells python to include data files in addition to python modules found in
    your repository.  This is necessary to ensure the web client assets are included
    in the package distribution.  See the
    `setuptools documentation <https://setuptools.readthedocs.io/en/latest/setuptools.html#including-data-files>`_
    for details.

``setup_requires=['setuptools-git']``
    This works with the ``include_package_data`` option to automatically include all non-python
    files that are checked into your git repository.  Alternatively, you can generate a
    ``MANIFEST.in`` for more fine-grained control over which files are included.

``packages=find_packages(exclude=['plugin_tests'])``
    This will include all python "packages" found inside the local path in the distribution
    with the exception of the ``plugin_tests`` directory.  If any other python modules or
    testing files are not desired in the distributed bundle, they should be added to this
    list.

``zip_safe=False``
    Unless this flag is provided, the python installer will install the package (and
    its non-python data files) as a python "egg".  Girder plugins including web
    extensions **do not** support this feature.

``install_requires=['girder>=3', 'girder_jobs']``
    This tells the installer that Girder of at least version 3 is required for this package
    to function.  When installing with ``pip``, Girder will be automatically installed
    from pypi if it is not already installed.  Any additional dependencies (including
    other Girder plugins) should be added to this list as well.

``entry_points={'girder.plugin': [ 'cats = girder_cats.CatsPlugin' ]}``
    This is the piece that registers your plugin with Girder's application.  When Girder
    starts up, it queries this entrypoint (``girder.plugin``) for all registered plugins.
    Here the name ``cats`` is the internal name registered to this plugin.  The value
    ``girder_cats.CatsPlugin`` is an import path resolving to a class that is expected
    to derive from ``girder.plugin.GirderPlugin``.  See below for an example of how to
    define this object.


Defining a Plugin Descriptor Class
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once you have created your ``setup.py`` file, you should begin to define the
python package that will contain your plugin.  In our case, we will name the
python package ``girder_cats`` so that it is a unique name on pypi ::

    mkdir girder_cats
    touch girder_cats/__init__.py

The base class at :py:class:`girder.plugin.GirderPlugin` defines the interface
between Girder and its plugins.  For advanced requirements, plugin authors can
override the properties defined on this class, but for most use cases inserting
the following into the top level ``__init__.py`` will suffice.

.. code-block:: python

    from girder.plugin import getPlugin, GirderPlugin

    class CatsPlugin(GirderPlugin):
        DISPLAY_NAME = 'Cats in Girder'
        CLIENT_SOURCE_PATH = 'web_client'

        def load(self, info):
            getPlugin('jobs').load(info)
            # attach endpoints, listen to events, etc...

Girder inspects attributes on this class for several pieces of metadata.  Most
of this metadata is automatically determined from the package-level metadata
defined in your ``setup.py`` file.  The additional attributes defined on this
class instance provide the following:

``DISPLAY_NAME``
    This provides Girder with a "user facing" name, e.g. a short description
    of the plugin not limited by the tokenization rules inherent in the "entrypoint
    name".  By default, the entrypoint name will be used if none is provided here.

``CLIENT_SOURCE_PATH``
    If your plugin contains a web client extension, you need to set this property
    to a path containing an npm package.  The path is always interpreted relative
    the python package install path.

Other optional attributes are defined on this class for more advanced use cases,
see the class documentation at :py:class:`girder.plugin.GirderPlugin` for details.


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

You can then attach this route to Girder in your plugin's load method

.. code-block:: python

    from girder.plugin import GirderPlugin
    class CatsPlugin(GirderPlugin)
      def load(self, info):
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

As done when extending an existing resource, this should be mounted into Girder's
API inside your plugin's load method:

.. code-block:: python

    from girder.plugin import GirderPlugin
    class CatsPlugin(GirderPlugin)
        def load(self, info):
            info['apiRoot'].cat = Cat()


Adding a prefix to an API
*************************

It is possible to provide a prefix to your API, allowing associated endpoints to
be grouped together. This is done by creating a prefix when mounting the resource.
Note that ``resourceName`` is **not** provided as the resource name is also derived
from the mount location.


.. code-block:: python

    from girder.api.rest import Resource, Prefix
    from girder.plugin import GirderPlugin

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

    class CatsPlugin(GirderPlugin):
        def load(self, info):
            info['apiRoot'].meow = Prefix()
            info['apiRoot'].meow.cat = Cat()

The endpoints are now mounted at meow/cat/


Adding a new model type in your plugin
**************************************

Most of the time, if you add a new resource type in your plugin, you'll have a
``Model`` class backing it. These model classes work just like the core model
classes as described in the :ref:`models` section. If you need to use the
:py:class:`~girder.utility.model_importer.ModelImporter` class with your model type,
you will need to explicitly register the model type to a string, e.g.

.. code-block:: python

    from girder.plugin import GirderPlugin
    from girder.utilities.model_importer import ModelImporter
    from .models.cat import Cat

    class CatsPlugin(GirderPlugin):
        def load(self, info):
            ModelImporter.registerModel('cat', Cat, plugin='cats')


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

    from girder_cat import Cat

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
        .modelParam('id', 'ID of the cat', model=Cat, level=AccessType.WRITE,
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

Customizing the Swagger page
****************************

To customize text on the Swagger page, create a
`Mako template <http://www.makotemplates.org/>`_ file that inherits from the
base template and overrides one or more blocks. For example,
``plugins/cats/server/custom_api_docs.mako``:

.. code-block:: html+mako

    <%inherit file="${context.get('baseTemplateFilename')}"/>

    <%block name="docsHeader">
      <span>Cat programming interface</span>
    </%block>

    <%block name="docsBody">
      <p>Manage your cats using the resources below.</p>
    </%block>

Install the custom template in the plugin's ``load`` function:

.. code-block:: python

    import os
    from girder.plugin import GirderPlugin

    PLUGIN_PATH = os.path.dirname(__file__)
    class CustomTemplatePlugin(GirderPlugin):
        def load(self, info):
            # Initially, the value of info['apiRoot'].templateFilename is
            # 'api_docs.mako'. Because custom_api_docs.mako inherits from this
            # base template, pass 'api_docs.mako' in the variable that the
            # <%inherit> directive references.
            baseTemplateFilename = info['apiRoot'].templateFilename
            info['apiRoot'].updateHtmlVars({
                'baseTemplateFilename': baseTemplateFilename
            })

            # Set the path to the custom template
            templatePath = os.path.join(PLUGIN_PATH, 'custom_api_docs.mako')
            info['apiRoot'].setTemplatePath(templatePath)

.. _client-side-plugins:

Extending the Client-Side Application
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The web client may be extended independently of the server side. Plugins may
import Pug templates, Stylus files, and JavaScript files into the application.
The plugin loading system ensures that only content from enabled plugins gets
loaded into the application at runtime.

All of your plugin's extensions to the web client must live in a directory inside
of your python package.  By convention, this is in a directory called **web_client**. ::

    cd girder_cats ; mkdir web_client

When present, this directory must contain a valid npm package, which includes a ``package.json``
file.  (See the `npm documentation <https://docs.npmjs.com/files/package.json>`_ for details.)
What follows is a typical npm package file for a Girder client side extension:

.. code-block:: json

    {
        "name": "@girder/cats",
        "version": "1.0.0",
        "peerDependencies": {
            "@girder/jobs": "*"
        },
        "dependencies": {
            "othermodule": "^1.2.4"
        },
        "girderPlugin": {
            "name": "cats",
            "main": "./main.js",
            "dependencies": ["jobs"],
            "webpack": "webpack.helper"
        }
    }


In addition to the standard ``package.json`` properties, Girder plugins
**must** also define a ``girderPlugin`` object to register themselves with
Girder's client build system.  The important keys in the object are as follows:

``name``
    This must be **exactly** the entrypoint name registered in your ``setup.py`` file.

``main``
    This is the entrypoint into your plugin on the client.  All runtime initialization
    should occur from here.

``dependencies``
    This is an array of entrypoint names that your plugin depends on.  Specifying this
    explicitly here is what allows Girder's client build system to build the plugin
    assets in the correct order.

``webpack``
    This is an optional property whose value is a node module that exports a
    function that can make arbitrary modification the webpack config used to
    build the plugin bundle.

    By default, Girder includes loaders for pug, stylus, css, fonts, and images
    in all paths.  For javascript inside the plugin, the code is transpiled
    through babel using ``babel-preset-env``; however, this is not done for
    dependencies resolved inside ``node_modules``.  This option makes it
    easy to include additional transpilation rules.  For an example of this in
    use, see the built in ``dicom_viewer`` plugin.

Core Girder code can be imported relative to the path **@girder/core**, for example
``import View from '@girder/core/views/View';``. The entry point defined in your
"main" file will be loaded into the browser after Girder's core library, but
before the application is initialized.



JavaScript extension capabilities
*********************************

Plugins may bind to any of the normal events triggered by core via a global
events object that can be imported like so:

.. code-block:: javascript

    import events from '@girder/core/events';

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

    import HierarchyWidget from '@girder/core/views/widgets/HierarchyWidget';
    import { wrap } from '@girder/core/utilities/PluginUtils';

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

    import events from '@girder/core/events';
    import router from '@girder/core/router';
    import { Layout } from '@girder/core/constants';
    import CollectionModel from '@girder/core/models/CollectionModel';
    import CollectionView from '@girder/core/views/body/CollectionView';

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

    add_standard_plugin_tests(PACKAGE "girder_cats")

This will automatically run static analysis tools on most parts of your plugin, including the
server, client, and testing files. Additionally, it will detect and run any tests in the special
``plugin_tests`` directory of your plugin, provided that server-side tests are named with the suffix
``_test.py`` (and the directory contains a ``__init__.py`` to make it a Python module) and
client-side tests are named with the suffix ``Spec.js``. For example:

.. code-block:: bash

    mkdir plugin_tests ; cd plugin_tests ; touch __init__.py cat_test.py catSpec.js

For more sophisticated configuration of plugin testing, options to ``add_standard_plugin_tests`` can
be used to disable some of the automatically-added tests, so they can be explicitly added with
additional options. See the ``add_standard_plugin_tests`` implementation for full option
documentation.

.. note::

    For auto-discovery of tests via plugin.cmake, you must copy your plugin's
    code inside Girder's ``/plugins`` directory.  This is the only case where
    the location of your plugin on the file system matters.

    TODO: We should think about an alternative discovery mechanism.


Testing Server-Side Code
************************

TODO: Replace this content with a pytest example.

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
the main Girder coverage results.

.. note:: Only files residing under the plugin's package directory will be included in coverage.
          See :ref:`python-coverage-paths` to change the paths used to generate Python coverage
          reports.

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

TODO: Should we deprecate/remove this capability for plugins?

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

Additionally, plugin developers can choose to extend or even entirely override Girder's default
static analysis rules, using
`ESLint's built-in configuration cascading <https://eslint.org/docs/user-guide/configuring#configuration-cascading-and-hierarchy>`_
(which is more fully documented in ESLint):

1. To extend or override some of Girder's default static analysis rules, place an ``.eslintrc.json``
   file in a directory with or above the target Javascript files.
2. To completely override all of Girder's default static analysis rules (i.e. disabling
   cascading), add root ``"root": true`` to an ``.eslintrc.json``.
3. To natively utilize Girder's default static analysis rules (from
   `their published location <https://www.npmjs.com/package/eslint-config-girder>`_) within code
   outside of Girder's ``plugins/`` directory structure, add ``"extends": "girder"`` to an
   ``.eslintrc.json``. However, this is not strictly necessary for an external Girder plugins that
   will be installed and tested under Girder's test framework (including the
   ``add_standard_plugin_tests`` CMake macro).

Finally, Javascript files within plugins' ``web_client/extra/`` directory will automatically
excluded from ESLint static analysis. To
`exclude additional Javascript files <https://eslint.org/docs/user-guide/configuring#disabling-rules-with-inline-comments>`_,
place an ``/* eslint-disable */`` block comment at the top of files to be excluded.
