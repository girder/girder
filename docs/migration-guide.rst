.. |ra| unicode:: 8594 .. right arrow

Migration Guide
===============

This document is meant to guide Girder plugin developers in transitioning
between major versions of Girder. Major version bumps contain breaking changes
to the Girder core library, which are enumerated in this guide along with
instructions on how to update your plugin code to work in the newer version.

3.x |ra| 5.x
------------

Major version 5 contains significant breaking changes on many fronts. The central theme of these
changes is to bring Girder into compliance with the principles of the
`12-factor app <https://12factor.net/>`_ to enhance its portability to various managed runtimes,
and in turn its ease of scalability. We chose to skip major version 4 due to a name collision with
Kitware's Django-based stack, which we had originally called Girder 4, but now refer to as Resonant
to distinguish it from this software.

The following are the breaking (or otherwise major) changes, ranked roughly in order of how
disruptive they are to downstream plugins:

Front-end build system changes
++++++++++++++++++++++++++++++

The largest change to Girder in version 5 is a complete overhaul of the front-end build system. Most
notably for users and plugin developers, the ``girder build`` command no longer exists, and Girder
itself will no longer manage the building of its plugins' web client bundles. Rather, each plugin is
responsible for building its own web client plugin code and exposing it via the following mechanism:

.. code-block:: python

    from pathlib import Path

    from girder.plugin import GirderPlugin, registerPluginStaticContent

    class Foo(GirderPlugin):
        DISPLAY_NAME = 'Foo'

        def load(self, info):
            registerPluginStaticContent(
                plugin='foo',
                css=['/style.css'],
                js=['/girder-plugin-foo.umd.cjs'],
                staticDir=Path(__file__).parent / 'web_client' / 'dist',
                tree=info['serverRoot'],
            )

Whatever files are passed into the ``js`` and ``css`` lists will be included in the core web client
after it loads. The ``staticDir`` argument should point to the directory containing the built web
client code, i.e. the filenames passed into the ``js`` and ``css`` lists are relative to this local
path. The ``tree`` argument should be the ``serverRoot`` object passed into the ``load`` method.

Changes within front-end plugin code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There is a mechanical conversion that will need to be performed on all front-end plugin code when
moving to Girder 5: rather than static ``import`` of symbols from ``@girder/core``
in your JavaScript/TypeScript code, you will instead rely on the presence of the ``girder`` symbol
in the global scope (``window.girder``) at runtime. Each import from ``@girder/core`` should be
changed as in the following examples:

Before:

.. code-block:: javascript

    import router from '@girder/core/router';
    import events from '@girder/core/events';
    import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

    import FrontPageView from '@girder/core/views/body/FrontPageView';
    import { renderMarkdown } from '@girder/core/misc';
    import { restRequest, getApiRoot } from '@girder/core/rest';
    import { wrap } from '@girder/core/utilities/PluginUtils';

After:

.. code-block:: javascript

    const router = girder.router;
    const events = girder.events;
    const { exposePluginConfig } = girder.utilities.PluginUtils;

    const FrontPageView = girder.views.body.FrontPageView;
    const { renderMarkdown } = girder.misc;
    const { restRequest, getApiRoot } = girder.rest;
    const { wrap } = girder.utilities.PluginUtils;


Static tooling
^^^^^^^^^^^^^^

If you are using vite as your plugin build tool, you can add the following to your ``vite-env.d.ts``
file to make TypeScript aware of the ``girder`` symbol, which enables things like IDE
autocompletion and jump-to-definition for symbols under the ``girder`` namespace.

.. code-block:: typescript

    /// <reference types="vite/client" />
    import { type Girder } from '@girder/core';

    declare global {
      const girder: Girder;
    }


Testing
^^^^^^^

Plugins are now also responsible for testing their own web client code. If your plugin was relying
on any of the old testing infrastructure, those tests will no longer work. We may publish our
Playwright-based front-end testing utilities as a separate package in the future, but as of 5.0,
it is not exposed to downstreams.

Removal of the events daemon
++++++++++++++++++++++++++++

The ``girder.events.daemon`` symbol has been removed, as the use of a background thread violated
the WSGI contract and tightly coupled Girder to a multi-threaded server model. The main impact of
this change is that any downstream users listening to the core ``"data.process"`` event,
which used to be run on the background thread, should now convert their event handlers to be
celery tasks or otherwise asynchronous methods if there's any risk of the handler taking more
than 1-2 seconds to complete.

Dynamic route configuration system removed
++++++++++++++++++++++++++++++++++++++++++

The server-side route table infrastructure that allowed dynamically updating URL paths from which
webroots would be served has been removed. URL routing should be known at startup time, and not
changed dynamically. This means that the ``girder.plugin.registerPluginWebroot`` function has been
removed.

The main challenge this presents is specifically for use cases where downstreams need to serve
the core Girder front-end application from a base path other than the server root (``/``), since
with the 5.0 front-end build changes, the front-end application is bundled in and built with a
static base of ``/``. For this specific use case, one strategy that's supported is to build the
core front-end application with a different base path, and then configure your server to serve
the modified front-end client from the desired path on the filesystem.

Example
^^^^^^^

In your plugin initialization function, add the following:

.. code-block:: python

    core_girder = info['serverRoot'].apps['']
    core_girder.script_name = '/new_root'
    info['serverRoot'].mount(core_girder, '/new_root', core_girder.config)
    del info['serverRoot'].apps['']
    # Mount your own app under `info['serverRoot']` if you want

Then, build the core front-end application with the desired base path:

.. code-block:: bash

    git clone git@github.com:girder/girder.git
    cd girder/girder/web
    npx vite build --base=/new_root/
    export GIRDER_STATIC_ROOT_DIR=$(pwd)/dist

With that variable set in your environment, the Girder core web client will now be served under
``/new_root/`` rather than ``/``.

Logging changes
+++++++++++++++

Girder's logging system was overhauled to adhere to
`12-factor logging principles <https://12factor.net/logs>`_. Use standard idiomatic Python
logging everywhere now, e.g.:

.. code-block:: python

    import logging
    logger = logging.getLogger(__name__)
    logger.info('My message')

The ``girder.logprint`` function was removed, and Girder will no longer write log messages to local
files on the server's filesystem. Additionally, the API endpoints for fetching logs and log info
were removed. Instead, logs are now written to standard output and it is up to the deployment
environment to direct them as needed. There are a huge variety of tools and strategies for log
management, so precise recommendations on log handlers are out of scope for Girder itself.

Config files removed
++++++++++++++++++++

The ``girder.local.cfg`` and ``girder.dist.cfg`` files are no longer used. Instead, all settings
should be passed in through the environment, or as command-line overrides in the case of using
``girder serve`` in development. Everything that was able to be controlled by the config file can
now be controlled by environment variables; see the
:ref:`configuration documentation <configuration_via_env>` for specifics on how to set these.

A notable change here is the configuration of the caching modules, which was previously done
via the config file alone. Now, the caching modules are configured via environment variables. e.g.

.. code-block:: bash

    GIRDER_SETTING_CORE_CACHE_ENABLED=true
    GIRDER_SETTING_CORE_CACHE_CONFIG='{"cache.global.backend": "dogpile.cache.redis", "cache.global.expiration_time": 7200}'

Config keys prefixed by ``cache.global.`` are used to configure the global dogpile cache, and
keys prefixed by ``cache.request.`` are used to configure the request cache.

WSGI app for production deployments
+++++++++++++++++++++++++++++++++++

Through load testing (as well as production usage), we discovered that cherrypy's built-in server
is not suitable for production use. It is not as performant as a dedicated WSGI server, and some
fraction of requests fail ungracefully under moderate load. As such, the ``girder serve`` command
is now only suitable for development and testing.

For production deployments, Girder now exposes a well-behaved WSGI app at ``girder.wsgi:app``.
Use a WSGI server such as gunicorn or uwsgi to serve in production. See
the :ref:`deployment documentation <deployment>` for an example gunicorn invocation.

Removal of the GridFS assetstore type
+++++++++++++++++++++++++++++++++++++

When we originally created the GridFS assetstore, it seemed like a reasonable blob storage solution.
However, in 2024, it is no longer a recommended solution for Girder. We have removed the GridFS
assetstore adapter type from the core codebase. If you are using GridFS, we recommend migrating your
data to a Filesystem or S3 assetstore type and deleting your GridFS assetstore prior to upgrading
to major version 5. There are many offerings in the cloud that support either the S3 or filesystem
assetstore adapter in a scalable way.

Python version support
++++++++++++++++++++++

Girder will now only maintain support for CPython versions that have not reached their end-of-life.
Check `this page <https://devguide.python.org/versions/>`_ to see the current status of upstream
Python version support. Note that this means we will feel free to use newer language features in
core as soon as they are available in the oldest supported version.

Changes to celery configuration in Worker plugin
++++++++++++++++++++++++++++++++++++++++++++++++

As we move to using celery in a more normal way, we now configure the celery app via the same code
path in both Girder server and the celery worker. Because we need to support deployment topologies
where the workers cannot communicate directly with the database, we cannot store celery
configuration in the mongo database. Instead, celery connectivity is now always configured via the
following environment variables:

* ``GIRDER_WORKER_BROKER``: The URL of the message broker to use for celery
* ``GIRDER_WORKER_BACKEND``: The URL of the result backend to use for celery

Switch to HttpOnly cookies in core web client
+++++++++++++++++++++++++++++++++++++++++++++

The ``auth.cookie`` symbol has been removed from the core web client. Cookies sent by the server
will now be set with the ``HttpOnly`` flag. This means that the cookies will no longer be
accessible to JavaScript, which is a security best practice. If you were relying on the
``auth.cookie`` symbol in your plugin, you should now use the ``auth.token`` symbol instead.

Note that cookies will still be sent and will still work for read-only endpoints that have
set the ``cookie=True`` property on their ``@access`` decorator.

Timezone aware datetime objects
+++++++++++++++++++++++++++++++

Due to deprecated behavior in Python 3.12, Girder now uses timezone-aware datetime objects.
If your code relied on the old behavior of naive datetimes, you may need to update it to
handle timezone-aware datetimes.

Removal of girder-worker command
++++++++++++++++++++++++++++++++

The ``girder-worker`` command has been removed because it didn't have the full configuration
powers of the underlying ``celery worker`` command. Instead, run ``celery worker`` directly:

.. code-block:: bash

    celery -A girder_worker.app worker


2.x |ra| 3.x
------------

Girder 3.0 changed how plugins are installed and loaded into the runtime
environment.  These changes require that **all** plugins exist as a standalone
python package.  Automatic loading of plugins from Girder's ``plugins``
directory is no longer supported.  This also applies to plugins that have no
server (python) component.

General plugin migration steps
++++++++++++++++++++++++++++++

The following is a list of changes that are necessary for a typical Girder
plugin:

* Create a ``setup.py`` in the root directory of your plugin.  A minimal example
  is as follows:

  .. code-block:: python

    from setuptools import setup
    setup(
        name='example-plugin',            # The name registered on PyPI
        version='1.0.0',
        description='An example plugin.', # This text will be displayed on the plugin page
        packages=['example_plugin'],
        install_requires=['girder'],      # Add any plugin dependencies here
        entry_points={
          'girder.plugin': [              # Register the plugin with girder.  The next line registers
                                          # our plugin under the name "example".  The name here must be
                                          # unique for all installed plugins.  The right side points to
                                          # a subclass of GirderPlugin inside your plugin.
              'example = example_plugin:ExamplePlugin'
          ]
        }
    )

* Move your plugin's python source code from the ``server`` directory to the package name defined
  in your ``setup.py``. In this example, you would move all python files from ``server`` to a new directory
  named ``example_plugin``.
* Move your ``web_client`` directory under the directory created in the previous step,
  which was ``example_plugin`` in the previous step.
* Create a ``package.json`` file inside your ``web_client`` directory defining an npm package.
  A minimal example is as follows:

  .. code-block:: javascript

    {
        "name": "@girder/my-plugin",
        "version": "1.0.0",
        "peerDepencencies": {
            "@girder/other_plugin": "*",      // Peer dependencies should be as relaxed as possible.
                                              // Add in any other girder plugins your plugin depends
                                              // on for web_client code.
                                              // Plugin dependencies should also be listed by entrypoint
                                              // name in "girderPlugin" as shown below.
            "@girder/core": "*"               // Your plugin will likely depend on girder/core.
        },
        "dependencies": {},                   // Any other dependencies of the client code
        "girderPlugin": {
            "name": "example",                // The entrypoint name defined in setup.py.
            "main": "./main.js"               // The plugin client entrypoint containing code that is executed on load.
            "webpack": "webpack.helper",      // If your plugin needs to modify the webpack config
            "dependencies": ["other_plugin"]  // If you plugin web_client requires another plugin
        }
    }

* Delete the ``plugin.json`` file at the root of your plugin. Move the ``dependencies`` from that file to
  the top level ``dependencies`` key of the ``package.json`` file created in the previous step.
* Create a subclass of :py:class:`girder.plugin.GirderPlugin` in your plugin package.  This class
  can be anywhere in your package, but a sensible place to put it is in the top-level ``__init__.py``.
  There are hooks for custom behavior in this class, but at a minimum you should move the old
  load method into this class and point to an npm package name containing your web client code.

  .. code-block:: python

    from girder.plugin import getPlugin, GirderPlugin

    class ExamplePlugin(GirderPlugin):
        DISPLAY_NAME = 'My Plugin'              # a user-facing plugin name, the plugin is still
                                                # referenced internally by the entrypoint name.
        CLIENT_SOURCE_PATH = 'web_client'       # path to the web client relative to the python package

        def load(self, info):
            getPlugin('mydependency').load(info)  # load plugins you depend on

            # run the code that was in the original load method

.. warning:: The plugin name was removed from the info object.  Where previously used, plugins should
             replace references to ``info['name']`` with a hard-coded string.

* Migrate all imports in Python and Javascript source files.  The old plugin module paths are no longer
  valid.  Any import reference to:

  * ``girder.plugins`` in Python must be changed to the actual installed module name

    * For example, change ``from girder.plugins.jobs.models.job import Job`` to
      ``from girder_jobs.models.job import Job``

  * ``girder_plugins`` in Javascript must be changed to the actual installed package name

    * For example, change ``import { JobListWidget } from 'girder_plugins/jobs/views';`` to
      ``import { JobListWidget } from '@girder/jobs/views';``

  * ``girder`` in Javascript must be changed to ``@girder/core``

    * For example, change ``import { restRequest } from 'girder/rest';`` to
      ``import { restRequest } from '@girder/core/rest';``


Other backwards incompatible changes affecting plugins
++++++++++++++++++++++++++++++++++++++++++++++++++++++

* Automatic detection of mail templates has been removed.  Instead, plugins should register
  them in their ``load`` method with :py:func:`girder.utility.mail_utils.addTemplateDirectory`.
* The ``mockPluginDir`` methods have been removed from the testing infrastructure.  If plugins
  need to generate a one-off plugin for testing, they can generate a subclass of
  :py:class:`girder.plugin.GirderPlugin` in the test file and register it in a test context
  with the ``test_plugin`` mark.  For example,

  .. code-block:: python

    class FailingPlugin(GirderPlugin):
        def load(self, info):
            raise Exception('This plugin fails on load')

    @pytest.mark.plugin('failing_plugin', FailingPlugin)
    def test_with_failing_plugin(server):
        # the test plugin will be installed in this context
* When running the server in testing mode (``girder serve --mode=testing``), the source directory
  is no longer served.  If you need any assets for testing, they have to be installed into
  the static directory during the client build process.
* Automatic registration of plugin models is no longer provided.  If your plugin contains any
  custom models that must be resolved dynamically (with ``ModelImporter.model(name, plugin=plugin)``)
  then you must register the model in your load method.  In the jobs plugin for example, we
  register the ``job`` model as follows:

  .. code-block:: python

    from girder.utility.model_importer import ModelImporter
    from .models.job import Job

    class JobsPlugin(GirderPlugin):
        def load(self, info):
            ModelImporter.registerModel('job', Job, 'jobs')

* In the web client, ``girder.rest.restRequest`` no longer accepts the deprecated ``path``
  parameter; callers should use the ``url`` parameter instead. Callers are also encouraged to use
  the ``method`` parameter instead of ``type``.

* The CMake function ``add_standard_plugin_tests`` can not detect the python package of your
  plugin.  It now requires you pass the keyword argument ``PACKAGE`` with the package name.
  For example, the jobs plugin ``plugin.cmake`` file contains the following line:

  .. code-block:: cmake

    add_standard_plugin_tests(PACKAGE "girder_jobs")

Client build changes
++++++++++++++++++++

The ``girder_install`` command has been removed.  This command was primarily
used to install plugins and run the client build.  Plugins should now be
installed (and uninstalled) using ``pip`` directly.  For the client build,
there is a new command, ``girder build``.  Without any arguments this command
will execute a production build of all installed plugins.  Executing ``girder
build --dev`` will build a *development* install of Girder's static assets as
well as building targets only necessary when running testing.

The new build process works by generating a ``package.json`` file in ``girder/web_client``
from the template (``girder/web_client/package.json.template``). The generated ``package.json``
itself depends on the core web client and all plugin web clients. The build process is executed in
place (in the Girder Python package) in both development and production installs. The built assets
are installed into a virtual environment specific static path ``{sys.prefix}/share/girder``.

Static public path is required during web client build
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The static `public path <https://webpack.js.org/guides/public-path/>`_, indicating the base URL
where web client files are served from, must now be known when the web client is built. Most
deployments can simply accept the default value of ``/static``, unless serving Girder from a CDN or
mounting at a subpath using a reverse proxy.

The static public path may be changed via the config file:

.. code-block:: ini

    [server]
    static_public_path = "/someprefix/static"

If the static public path setting is changed, the web client must be immediately rebuilt.

The static public path setting replaces all previous "static root" functionality. Accordingly:

* The server now serves all static content from ``/static``. The ``GIRDER_STATIC_ROUTE_ID`` constant
  has been removed.
* In the server, ``girder.utility.server.getStaticRoot`` has been removed.
* In the web client, ``girder.rest.staticRoot``, ``girder.rest.getStaticRoot``, and
  ``girder.rest.setStaticRoot`` have been removed.
* The ability to set the web client static root / public path via the special element
  ``<div id="g-global-info-staticroot">`` has been removed

Server changes
++++++++++++++

The ``GET /user`` API endpoint is only open to logged-in users
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is a policy change from 2.x, in which this endpoint was publicly accessible. Since user name
data may be considered sensitive, and many Girder instances have controlled registration policies,
it made sense to change this access policy.

ModelImporter behavior changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :py:class:`girder.utility.model_importer.ModelImporter` class allows model types to be mapped
from strings, which is useful when model types must be provided by users via the REST API. In Girder
2, there was logic to infer automatically where a model class resides without having to explicitly
register it, but that logic was removed. If your plugin needs to expose a ``Model`` subclass for
string-based lookup, it must be explicitly registered, e.g.

.. code-block:: python

  class MyModel(Model):
     ...

  ModelImporter.registerModel('my_plugin_model', MyModel, plugin='my_plugin')

The ``load`` method of your plugin is a good place to register your plugin's models.

In addition to explicitly requiring registration, the API of
:py:meth:`~girder.utility.model_importer.ModelImporter.registerModel` has also changed. Before, one
would pass the model *instance*, but now, one passes the model *class*.

.. code-block:: python

   # Girder 2:
   ModelImporter.registerModel('my_thing', MyThing())

   # Girder 3:
   ModelImporter.registerModel('my_thing', MyThing)

Additionally, several key base classes in Girder no longer mixin ``ModelImporter``, and mixing it
in is now generally discouraged. So instead of ``self.model``, just use ``ModelImporter.model`` if
you must convert a string to a model instance. The following base classes are affected:

* :py:class:`girder.api.rest.Resource`
* :py:class:`girder.models.model_base.Model`
* :py:class:`girder.utility.abstract_assetstore_adapter.AbstractAssetstoreAdapter`

Multipart-encoded upload chunk support has been removed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Prior to version 3, Girder supported ``multipart/form-data`` content type for passing fields into
the ``POST /file/chunk`` endpoint. This has been deprecated since v2.2, and has been removed. Now,
the ``uploadId`` and ``offset`` fields should be passed in the query string, and the chunk data
should be passed as the request body.

Event bindings are now unique by handler name
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In Girder 2, it was possible to bind multiple handler callbacks to the same event with
the same handler name. This has changed in Girder 3; for any given event identifier, each callback
must be bound to it with a unique handler name. Example:

.. code-block:: python

    def cb(event):
       print('hello')

    for _ in range(5):
      events.bind('an_event', 'my_handler', cb)

    # Prints 'hello' five times in Girder 2, but only once in Girder 3
    events.trigger('an_event')

In the new behavior, a call to ``bind`` with the same event name and handler name as an existing
handler will be ignored, and will emit a warning to the log. If you wish to overwrite the existing
handler, you must call :py:func:`girder.events.unbind` on the existing mapping first.

.. code-block:: python

    def a(event):
      print('a')

    def b(event):
      print('b')

    events.bind('an_event', 'my_handler', a)
    events.bind('an_event', 'my_handler', b)

    # Prints 'a' and 'b' in Girder 2, but only 'a' in Girder 3
    events.trigger('an_event')

Async keyword arguments and properties changed to async\_ PR #2817
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In version 3.7 of python ``async`` is a `reserved keyword argument <https://www.python.org/dev/peps/pep-0492/#deprecation-plans/>`_.
To mitigate any issues all instances of ``async`` in the codebase have changed to ``asynchronous``.
This affects:

 * The event framework ``girder/events.py``
 * The built-in job plugin ``plugins/jobs/girder_jobs/models/job.py``

The cookie access decorator has been removed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``@access.cookie`` decorator has been removed.  To allow cookie authentication on an endpoint, include ``cookie=True`` as a parameter to one of the other access decorators (e.g., ``@access.user(cookie=True)``).

Storing girder.local.cfg inside the package directory is no longer supported
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In order to facilitate the ability to upgrade Girder using ``pip``, the user configuration file
can no longer be stored inside the package directory since it would be deleted on upgrade. Users must
now store their configuration in one of the approved locations, or use ``GIRDER_CONFIG`` to specify
the exact location. See :ref:`the configuration documentation <configuration>` for more details.

Invoking Girder and Girder Client with python -m is no longer supported
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Using ``python -m girder`` and ``python -m girder-cli`` was deprecated in Girder 2.5 and is no longer supported.
Users are expected to have the appropriate packages installed and then use ``girder serve`` and ``girder-client``
respectively.

Removed insecure sha512 password hashing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The ``core.hash_alg`` and ``core.bcrypt_rounds`` configuration parameters were also removed.
Password hashing now always occurs with 12-round bcrypt. Please reach out to us on `Github Discussions <https://github.com/orgs/girder/discussions>`_` if you
have existing databases with sha512 passwords or believe you need to configure bcrypt to use
additional rounds.

Core setting constants now reside in settings.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The ``SettingKey`` and ``SettingDefault`` classes (which contain constants for core settings) must
now be imported from the ``girder.settings`` module.

.. code-block:: python

    from girder.settings import SettingDefault, SettingKey

The API for sending email has changed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The ``mail_utils.sendEmail`` function has been replaced with several new functions:
``mail_utils.sendMailSync``, ``mail_utils.sendMail``, ``mail_utils.sendMailToAdmins``,
``mail_utils.sendMailIndividually``. Note that the argument order and expected types have changed.
See function documentation for details on the new usage.

Removed or moved plugins
++++++++++++++++++++++++

Many plugins were either deleted from the main repository, or moved to other repositories. Plugins
are no longer installable via a ``[plugins]`` extra when installing the ``girder`` Python package;
rather, all are installed by ``pip install girder-[plugin_name]``. If you were depending on a plugin
that was deleted altogether, please reach out to us on `Github Discussions <https://github.com/orgs/girder/discussions>`_ for discussion of a path forward.

The following plugins were **deleted**:

* celery_jobs
* item_previews
* jquery_widgets
* metadata_extractor
* mongo_search
* provenance
* treeview
* vega

The following plugins were **moved to different repositories**:

* `candela <https://github.com/kitware/candela>`_
* `curation (renamed to publication_approval) <https://github.com/girder/girder-publication-approval>`_
* `geospatial <https://github.com/OpenGeoscience/girder_geospatial>`_
* `hdfs_assetstore <https://github.com/girder/girder-hdfs-assetstore>`_
* `item_tasks <https://github.com/girder/girder-item-tasks>`_
* `table_view <https://github.com/girder/girder-table-view>`_
* `worker <https://github.com/girder/girder_worker>`_

1.x |ra| 2.x
------------

Existing installations may be upgraded to the latest 2.x release by running
``pip install -U girder<3`` and re-running ``girder-install web``. You may need
to remove ``node_modules`` directory from the installed girder package if you
encounter problems while re-running ``girder-install web``. Note that the
prerequisites may have changed in the latest version: make sure to review
:doc:`dependencies` prior to the upgrade.

Server changes
++++++++++++++

* The deprecated event ``'assetstore.adapter.get'`` has been removed. Plugins using this event to
  register their own assetstore implementations should instead just call the
  ``girder.utility.assetstore_utilities.setAssetstoreAdapter`` method at load time.
* The ``'model.upload.assetstore'`` event no longer supports passing back the target assetstore by adding
  it to the ``event.info`` dictionary. Instead, handlers of this event should use ``event.addResponse``
  with the target assetstore as the response.
* The unused ``user`` parameter of the ``updateSize`` methods in the collection, user, item, and
  folder models has been removed.
* The unused ``user`` parameter of the ``isOrphan`` methods in the file, item, and folder models
  has been removed.
* Several core models supported an older, nonstandard kwarg format in their ``filter`` method.
  This is no longer supported; the argument representing the document to filter is now always
  called ``doc`` rather than using the model name for the kwarg. If you were using positional args
  or using the ``filtermodel`` decorator, this change will not affect your code.
* Multiple configurable plugin loading paths are no longer supported. Use
  ``girder-install plugin <your_plugin_path>`` to install plugins that are not already in the
  plugins directory. Pass ``-s`` to that command to symlink instead of copying the directory.
  This also means:

    * The ``plugins.plugin_directory`` and ``plugins.plugin_install_path`` config file settings
      are no longer supported, but their presence will not cause problems.
    * The ``defaultPluginDir``, ``getPluginDirs``, ``getPluginParentDir`` methods inside ``girder.utility.plugin_utilities``
      were removed.
    * All of the methods in ``girder.utility.plugin_utilities`` no longer accept a ``curConfig``
      argument since the configuration is no longer read.

* The ``girder.utility.sha512_state`` module has been removed.
* The ``girder.utility.hash_state`` module has been made private. It should not be used downstream.


Web client changes
++++++++++++++++++

* In version 1.x, running ``npm install`` would install our npm dependencies, as well as run the
  web client build process afterwards. That is no longer the case; ``npm install`` now only installs
  the dependencies, and the build is run with ``npm run build``.

    * The old web client build process used to build *all available* plugins in the plugin directory.
      Now, running ``npm run build`` will *only build the core code*. You can pass a set of plugins
      to additionally build by passing them on the command like, e.g. ``npm run build -- --plugins=x,y,z``.
    * The ``grunt watch`` command has been deprecated in favor of ``npm run watch``. This also only
      watches the core code by default, and if you wish to also include other plugins, you should
      pass them in the same way, e.g. ``npm run watch -- --plugins=x,y,z``.
    * The ``girder-install web`` command is now the recommended way to build web client code. It
      builds all *enabled* plugins in addition to the core code. The ability to rebuild the web
      client code for the core and all enabled plugins has been exposed via the REST API and the
      admin console of the core web client. The recommended process for administrators is to turn
      on all desired plugins via the switches, click the **Rebuild web code** button, and once that
      finishes, click the button to restart the server.
* **Jade** |ra| **Pug** rename: Due to trademark issues, our upstream HTML templating engine was renamed from
  Jade to Pug. In addition, this rename coincides with a major version bump in the language which comes
  with notable breaking changes.

    * Template files should now end in ``.pug`` instead of ``.jade``. This affects how they are imported as modules
      in webpack.
    * Jade-syntax interpolation no longer works inside string values of attributes. Use ES2015-style string
      templating instead. Examples:

        * ``a(href="#item/#{id}/foo")`` |ra| ``a(href=`#item/${id}/foo`)``
        * ``.g-some-element(cid="#{obj.cid}")`` |ra| ``.g-some-element(cid=obj.cid)``
    * Full list of breaking changes are listed `here <https://github.com/pugjs/pug/issues/2305>`_, though
      most of the others are relatively obscure.
* Testing specs no longer need to manually import all of the source JS files under test. We now have
  better source mapping in our testing infrastructure, so it's only necessary to import the built
  target for your plugin, e.g.

    * 1.x:

      .. code-block:: javascript

        girderTest.addCoveredScripts([
            '/static/built/plugins/jobs/templates.js',
            '/plugins/jobs/web_client/js/misc.js',
            '/plugins/jobs/web_client/js/views/JobDetailsWidget.js',
            '/plugins/jobs/web_client/js/views/JobListWidget.js'
        ]);

    * 2.x:

      .. code-block:: javascript

        girderTest.importPlugin('jobs');

* **Build system overhaul**: Girder web client code is now built with `Webpack <https://webpack.github.io/>`_
  instead of uglify, and we use the `Babel <https://babeljs.io/>`_ loader to enable ES2015 language support.
  The most important result of this change is that plugins can now build their own targets
  based on the Girder core library in a modular way, by importing specific components.
  See the :ref:`plugin development guide<client-side-plugins>` for a comprehensive guide on
  developing web-client plugins in the new infrastructure.

Python client changes
+++++++++++++++++++++

* Girder CLI: Subcommands are no longer specified with the ``-c`` option. Instead, the subcommand is
  specified just after all the general flags used for connection and authentication. For example:

    * Before: ``girder-cli --api-key=abcdefg --api-url=https://mygirder.org/api/v1 -c upload 1234567890abcdef ./foo``
    * After: ``girder-cli --api-key=abcdefg --api-url=https://mygirder.org/api/v1 upload 1234567890abcdef ./foo``
* The ``blacklist`` and ``dryrun`` kwargs are no longer available in the ``GirderClient``
  constructor because they only apply to uploading. If you require the use of a blacklist, you
  should now pass it into the ``upload`` method. These options can still be passed on the CLI,
  though they should now come *after* the ``upload`` subcommand argument.
* Legacy method names in the ``GirderClient`` class API have been changed to keep naming convention
  consistent.

    * ``add_folder_upload_callback`` |ra| ``addFolderUploadCallback``
    * ``add_item_upload_callback`` |ra| ``addItemUploadCallback``
    * ``load_or_create_folder`` |ra| ``loadOrCreateFolder``
    * ``load_or_create_item`` |ra| ``loadOrCreateItem``
* All kwargs to ``GirderClient`` methods have been changed from **snake_case** to **camelCase** for
  consistency.
* Listing methods in the ``GirderClient`` class (e.g. ``listItem``) have been altered to be
  generators rather than return lists. By default, they will now iterate until exhaustion, and
  callers won’t have to pass ``limit`` and ``offset`` parameters unless they want a specific slice
  of the results. As long as you are just iterating over results, this will not break your existing
  code, but if you were using other operations only available on lists, this could break. The
  recommended course of action is to modify your logic so that you only require iteration over the
  results, though it is possible to simply wrap the return value in a ``list()`` constructor. Use
  caution if you use the ``list()`` method, as it will load the entire result set into memory.

Built-in plugin changes
+++++++++++++++++++++++

* **Jobs**: The deprecated ``jobs.filter`` event was removed. Use the standard ``exposeFields`` and
  ``hideFields`` methods on the job model instead.
* **OAuth**: For legacy backward compatibility, the Google provider was previously enabled by
  default. This is no longer the case.
