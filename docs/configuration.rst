Configuration
=============

In many cases, Girder will work with default configuration whether installed via
pip or from a source checkout or tarball. That said, the Girder config file can
be set at the following locations (ordered by precedent):

#. The path specified by the environment variable `GIRDER_CONFIG`.
#. ~/.girder/girder.cfg
#. /etc/girder.cfg
#. /path/to/girder/package/conf/girder.local.cfg
#. /path/to/girder/package/conf/girder.dist.cfg

Logging
-------

Much of Girder's output is placed into the error or info log file. By default,
these logs are stored in ~/.girder/logs. To set the Girder log root or error and
info logs specifically, set the `log_root`, `error_log_file`, and/or
`info_log_file` variables in the `logging` config group. If `log_root` is set,
error and info will be set to error.log and info.log within `log_root`
respectively. The `_log_file` variables will override that setting and are
*absolute* paths.

Server thread pool
------------------

Girder can handle multiple requests at one time.  The maximum number of
simultaneous requests is set with the `server.thread_pool` value in the
`global` config group.  Once this many connections have been made to Girder,
additional connections will block until existing connections finish.

Most operations on Girder are quick, and therefore do not use up a connection
for a long duration.  Some connections, notably calls to the
`notification/stream` endpoint, can block for long periods.  If you expect to
have many clients, either increase the size of the thread pool or switch to
using intermittent polling rather than long-duration connections.

Each available thread uses up some additional memory and requires internal
socket or handle resources.  The exact amount of memory and resources is
dependent on the host operating system and the types of queries made to Girder.
As one benchmark from an Ubuntu server, each additional available but unused
connection requires roughly 25 kb of memory.  If all connections are serving
notification streams, each uses around 50 kb of memory.

Changing file limits
....................

If all server threads are in use, additional attempts to connect will use a
file handle while waiting to be processed.  The number of open files is limited
by the operating system, and may need to be increased.  This limit affects
actual connections, pending connections, and file use.

The method of changing file limits varies depending on your operating system.
If your operating system is not listed here, try a web search for "Open Files
Limit" along with your OS's name.

Linux
'''''

You can query the current maximum number of files with the command: ::

    ulimit -Sn

To increase this number for all users, as root or with sudo privileges, edit
``/etc/security/limits.conf`` and append the following lines to the end of the
file: ::

    *    soft    nofile    32768
    *    hard    nofile    32768

Save and close the file.  The user running the Girder server will need
to logout and log back in and restart the Girder server for the new limits
to take effect.

This raises the limits for all users on the system.  You can limit this change
to just the user that runs the Girder server.  See the documentation for
``/etc/security/limits.conf`` for details.

.. _managing-routes:

Managing Routes
---------------

When plugins which have their own custom webroot are enabled, they are mounted at /pluginName.
In certain cases it may be desirable for the site administrator to mount such plugins at their own
specified paths.

These paths can be modified by navigating to Admin Console -> Server Configuration and
visiting the Routing section.

