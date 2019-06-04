.. _python-client:

Python Client and Girder CLI
============================

In addition to the web clients, Girder comes with a python client library and
a CLI to allow for programmatic interaction with a Girder server, and also to
workaround limitations of the web client. For example, the python CLI makes it
much easier to upload a large, nested hierarchy of data from a local directory
to Girder, and also makes it much easier to download a large, nested hierarchy
of data from Girder to a local directory.

Installation
------------

If you have the source directory of Girder, you can find the ``girder_client``
package within the ``clients/python`` directory. If you do not have the source
directory of Girder, you can install the client via pip: ::

    pip install girder-client


After installing the client via pip and if you are using ``bash``,
auto-completion can easily be enabled executing:

::

    eval "$(_GIRDER_CLI_COMPLETE=source girder-client)"

For convenience, adding this line at the end of ``.bashrc`` will make sure
auto-completion is always available.

For more details, see http://click.pocoo.org/6/bashcomplete/

The Command Line Interface
--------------------------

The girder_client package ships with a command-line utility that wraps some of
its common functionality to make it easy to invoke operations without having
to write any custom python scripts. If you have installed girder_client via
pip, you can use the ``girder-client`` executable: ::

    girder-client <arguments>

To see all available commands, run: ::

    girder-client --help

For help with a specific command, run: ::

    girder-client <command> --help

Specifying the Girder Instance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When constructing a Girder client, you must declare what instance of Girder
you wish to connect to. The easiest way to do so is to pass the full URL to the
REST API of the Girder instance you wish to connect to using the ``api-url``
argument to ``girder-client``. For example: ::

    girder-client --api-url http://localhost:8080/api/v1 <command> ...


Instead of using ``api-url`` argument, you may also specify the URL in parts, using the
``host`` argument, and optional ``scheme``, ``port``, and ``api-root`` args.

Specifying credentials
^^^^^^^^^^^^^^^^^^^^^^

The recommended way is to generate an :ref:`API key <api_keys>` and specify
the ``api-key`` argument. ::

    girder-client --api-url https://girder.example.com:443/api/v1  --api-key abcdefghijklmopqrstuvwxyz012345678901234 ...

Setting the ``GIRDER_API_KEY`` environment variable is also supported: ::

    export GIRDER_API_KEY=abcdefghijklmopqrstuvwxyz012345678901234
    girder-client --api-url https://girder.example.com:443/api/v1 ...

The client also supports ``username`` and ``password`` args. If only the
``username`` is specified, the client will prompt the user to interactively
input their password.

Disabling SSL verification
^^^^^^^^^^^^^^^^^^^^^^^^^^

Specifying ``--no-ssl-verify`` allows to ignore SSL verification. This is
usually required when using the client behind a proxy that is not configured to
accept the certificate of the given host.

Specifying a custom SSL certificate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Specifying ``--certificate /path/to/custom_bundle.pem`` allows to use a custom "bundle" of
Certificate Authority (CA) public keys (CA certs) for performing the SSL verification
applied when the ``https`` scheme is associated with the API url.

By default, the carefully curated collection of Root Certificates from Mozilla is used.
See https://pypi.python.org/pypi/certifi

Upload a local file hierarchy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To upload a folder hierarchy rooted at `test_folder` to the Girder Folder with
id `54b6d41a8926486c0cbca367` ::


    girder-client upload 54b6d41a8926486c0cbca367 test_folder

When using the upload command, the default ``--parent-type``, meaning the type
of resource the local folder will be created under in Girder, is Folder, so the
following are equivalent ::

    girder-client upload 54b6d41a8926486c0cbca367 test_folder
    girder-client upload 54b6d41a8926486c0cbca367 test_folder --parent-type folder

To upload that same local folder to a Collection or User, specify the parent
type as follows ::

    girder-client upload 54b6d41a8926486c0cbca459 test_folder --parent-type user

To see what local folders and files on disk would be uploaded without actually
uploading anything, add the ``--dry-run`` flag ::

    girder-client upload 54b6d41a8926486c0cbca367 test_folder --dry-run

To have leaf folders (those folders with no subfolders, only containing files)
be uploaded to Girder as single Items with multiple Files, i.e. those leaf
folders will be created as Items and all files within the leaf folders will be
Files within those Items, add the ``--leaf-folders-as-items`` flag ::

    girder-client upload 54b6d41a8926486c0cbca367 test_folder --leaf-folders-as-items

If you already have an existing Folder hierarchy in Girder which you have a
superset of on your local disk (e.g. you previously uploaded a hierarchy to
Girder and then added more folders and files to the hierarchy on disk), you can
reuse the existing hierarchy in Girder, which will not create new Folders and
Items for those that match folders and files on disk, by using the ``--reuse`` flag.

::

    girder-client upload 54b6d41a8926486c0cbca367 test_folder --reuse

To include a blacklist of file patterns that will not be uploaded, pass a comma
separated list to the ``--blacklist`` arg ::

    girder-client upload 54b6d41a8926486c0cbca367 test_folder --blacklist .DS_Store

.. note: The girder_client can upload to an S3 Assetstore when uploading to a Girder server
         that is version 1.3.0 or later.

Download a hierarchy of data into a local folder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Folder
""""""

To download a Girder Folder hierarchy rooted at Folder id
`54b6d40b8926486c0cbca364` under the local folder `download_folder` ::

    girder-client download 54b6d40b8926486c0cbca364 download_folder


Collection
""""""""""

To download the Girder Folder hierarchies associated with a Girder Collection
with id `57b5c9e58d777f126827f5a1` under the local folder `download_folder` ::

    girder-client download --parent-type collection 57b5c9e58d777f126827f5a1 download_folder

User
""""

To download the Girder Folder hierarchies associated with a Girder User
with id `54f8ac238d777f69813604af` under the local folder `download_folder` ::

    girder-client download --parent-type user 54b6d40b8926486c0cbca364 download_folder

Item
""""

To download the file(s) associated with a Girder Item with if `58b8eb798d777f0aef5d0f78` under
the local folder `download_folder`::

    girder-client download --parent-type item 8b8eb798d777f0aef5d0f78 download_folder

File
""""

To download a specific file from girder with id `58b8eb798d777f0aef5d0f78` to
the local file `local_file` ::

    girder-client download --parent-type file 8b8eb798d777f0aef5d0f78  local_file


Auto-detecting parent-type
^^^^^^^^^^^^^^^^^^^^^^^^^^

Both download and upload commands accept a `--parent-type` argument allowing the users
to specify the type (folder, collection, user, or item) associated with the chosen
object id.

If the argument is omitted, the client will conveniently try to autodetect the type
by iteratively invoking the `resource/%id/path?type=%type` API end point and checking
if a resource is found.

Note that relying on auto-detection incurs extra network requests, which will slow down
the script, so it should be avoided for time-sensitive operations.

Synchronize local folder with a Folder hierarchy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the `download_folder` is a local copy of a Girder Folder hierarchy rooted at
Folder id `54b6d40b8926486c0cbca364`, any change made to the Girder Folder remotely
can be synchronized locally by ::

    girder-client localsync 54b6d40b8926486c0cbca364 download_folder

This will only download new Items or Items that have been modified since the
last download/localsync. Local files that are no longer present in the remote
Girder Folder will not be removed. This command relies on a presence of
metadata file `.metadata-girder` within `download_folder`, which is created
upon `girder-client download`. If `.metadata-girder` is not present,
`localsync` will fallback to `download`.

The Python Client Library
-------------------------

For those wishing to write their own python scripts that interact with Girder,
we recommend using the Girder python client library, documented below.

Recursively inherit access control to a Folder's descendants
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This will take the access control and public value in the Girder Folder with
id `54b43e9b8926486c0c06cb4f` and copy those to all of the descendant Folders

.. code-block:: python

    import girder_client
    gc = girder_client.GirderClient(apiUrl='https://data.kitware.com/api/v1')
    gc.authenticate('username', 'password')
    gc.inheritAccessControlRecursive('54b43e9b8926486c0c06cb4f')

Set callbacks for Folder and Item uploads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have a function you would like called upon the completion of an Item
or Folder upload, you would do the following.

N.B. The Item callbacks are called after the Item is created and all Files are uploaded to
the Item. The Folder callbacks are called after the Folder is created and all child Folders
and Items are uploaded to the Folder.


.. code-block:: python

    import girder_client
    gc = girder_client.GirderClient()

    def folderCallback(folder, filepath):
        # assume we have a folderMetadata dict that has
        # filepath: metadata_dict_for_folder
        gc.addMetadataToFolder(folder['_id'], folderMetadata[filepath])

    def itemCallback(item, filepath):
        # assume we have an itemMetadata dict that has
        # filepath: metadata_dict_for_item
        gc.addMetadataToItem(item['_id'], itemMetadata[filepath])

    gc.authenticate('username', 'password')
    gc.addFolderUploadCallback(folderCallback)
    gc.addItemUploadCallback(itemCallback)
    gc.upload(localFolder, parentId)


Further Examples and Function Level Documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: girder_client
    :special-members: __init__
    :members:
