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

Web client changes
++++++++++++++++++

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

