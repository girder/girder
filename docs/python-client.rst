Python Client and Girder CLI
============================

In addition to the web clients, Girder comes with a python client library and
a CLI to allow for programmatic interaction with a Girder server, and also to
workaround limitations of the web client. For example, the python CLI makes it
much easier to upload a large, nested hierarchy of data from a local directory
to Girder, and also makes it much easier to download a large, nested hierarchy
of data from Girder to a local directory.

The Command Line Interface
--------------------------

To see the options beyond those described here:

    python cli.py
    
Upload a local file hierarchy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `upload` command is the default, so the following two forms are equivalent:

    python cli.py
    python cli.py -c upload

To upload a folder hierarchy rooted at `test_folder` to the Girder Folder with
id `54b6d41a8926486c0cbca367`:

    python cli.py 54b6d41a8926486c0cbca367 test_folder

When using the `upload` command, the default parent type--meaning the type of
resource the local folder will be created under--is Folder, so the
following are equivalent:

    python cli.py 54b6d41a8926486c0cbca367 test_folder
    python cli.py 54b6d41a8926486c0cbca367 test_folder --parent-type folder

To upload that same local folder to a Collection or User, specify the parent
type as follows:

    python cli.py 54b6d41a8926486c0cbca459 test_folder --parent-type user

To see what local folders and files on disk would be uploaded without actually
uploading anything, add the `--dryrun` flag:

    python cli.py 54b6d41a8926486c0cbca367 test_folder --dryrun

To have leaf folders (those with no subfolders, only containing files) be
uploaded to Girder as single Items with multiple Files (those files contained
in the folders), add the `--leaf-folders-as-items` flag:

    python cli.py 54b6d41a8926486c0cbca367 test_folder --leaf-folders-as-items

If you already have an existing Folder hierarchy in Girder which you have a 
superset of on your local disk (e.g. you uploaded a hierarchy and then added
more folders and files to the hierarchy on disk), you can reuse the existing
hiearchy in Girder, which will not create new Folders and Items for those that
match folders and files on disk by using the `--reuse` flag.

    python cli.py 54b6d41a8926486c0cbca367 test_folder --reuse
  
To include a blacklist of filepatterns that will not be uploaded, pass a comma
separated list to the `--blacklist` arg:

    python cli.py 54b6d41a8926486c0cbca367 test_folder --blacklist .DS_Store

Download a Folder hierarchy into a local folder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To download a Girder Folder hierarchy rooted at Folder id
`54b6d40b8926486c0cbca364` under the local folder `download_folder`:
    
    python cli.py -c download 54b6d40b8926486c0cbca364 download_folder

Downloading is only supported from a parent type of Folder.

The Python Client Library
-------------------------

For those wishing to write their own python scripts that interact with Girder,
we recommend using the Girder python client library, documented below.
   
Recursively inherit access control to a Folder's descendants
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This will take the access control and public value in the Girder Folder with
id `54b43e9b8926486c0c06cb4f` and copy those to all of the descendant Folders:

    import girder_client
    gc = girder_client.GirderClient()
    gc.authenticate('username', 'password')
    gc.inheritAccessControlRecursive('54b43e9b8926486c0c06cb4f')


def inheritAccessControlRecursive(self, ancestorFolderId, access=None,

.. automodule:: girderclient
    :members:
