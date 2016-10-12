.. |ra| unicode:: 8594 .. right arrow

Migration Guide
===============

This document is meant to guide Girder plugin developers in transitioning
between major versions of Girder. Major version bumps contain breaking changes
to the Girder core library, which are enumerated in this guide along with
instructions on how to update your plugin code to work in the newer version.

1.x |ra| 2.x
------------

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
  or using the ``filterModel`` decorator, this change will not affect your code.
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

* The ``girder.utility.sha512_state`` module has been removed. All of its symbols had been deprecated
  and replaced by corresponding ones in ``girder.utility.hash_state``.

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
  jade to pug. In addition, this rename coincides with a major version bump in the language which comes
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

        girderTest.addCoveredScripts([
            '/clients/web/static/built/plugins/jobs/plugin.min.js'
        ]);

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
