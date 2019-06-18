Girder FUSE Mount
-----------------

The files in Girder can be mounted in a user file system (FUSE).  The allows
Girder plugins and C extensions that cannot directly access Girder files to
read them as if they were physical files.  This allows external libraries that
require file access to read Girder files, regardless of which assetstore they
are stored on.  It also uses the underlying operating system's caching to
improve reading these files.

Additionally, some C extensions expect multiple files in the same Girder item
to be stored in the same directory and with specific file extensions.  When a
Girder FUSE mount is available, these will work -- instead of passing the
Girder file object, call `File().getGirderMountFilePath()` to get a path to the
file.

To enable a Girder FUSE mount, run ``girder mount <mount path>``, where
``<mount path>`` is an empty directory.  This can be done before or after a
Girder server is started -- the mount process sets a value in the Girder Mongo
database to inform Girder servers where the mount is located.

The mount can be unmounted used ``girder mount <mount path> -u`` or with
standard system unmount commands (e.g., ``fusermount -u <mount path>`` or
``sudo umount <mount path>``.

.. note:: If the Girder mount process is sent ``SIGKILL`` with open file handles, it may not be possible to fully clean up the open file system, and defunct processes may linger.  This is a limitation of libfuse, and may require a reboot to clear the lingering mount.  Use an unmount command or ``SIGTERM``. 

Installation
++++++++++++

There are some additional python dependencies to use the Girder mount commnd. 
These can be installed via: ::

  $ pip install -e .[mount] 

