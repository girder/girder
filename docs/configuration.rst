Configuration
=============

.. _configuration:

In many cases, Girder will work with default configuration whether installed via
pip or from a source checkout or tarball. That said, the Girder config file can
be set at the following locations (ordered by precedent):

#. The path specified by the environment variable `GIRDER_CONFIG`.
#. ~/.girder/girder.cfg
#. /etc/girder.cfg

Logging
-------

Much of Girder's output is placed into the error or info log file. By default,
these logs are stored in ~/.girder/logs. To set the Girder log root or error and
info logs specifically, set the `log_root`, `error_log_file`, and/or
`info_log_file` variables in the `logging` config group. If `log_root` is set,
error and info will be set to error.log and info.log within `log_root`
respectively. The `_log_file` variables will override that setting and are
*absolute* paths.

Log files are written to until they reach a specified size.  They are then
rotated, keeping a number of files before the oldest file is deleted.  The size
of the files can be set via the `log_max_size` setting.  This is either an
integer value in bytes or a string with a integer value followed by a 'kb',
'Mb', or 'Gb' suffix.  The number of files can be adjusted using the
`log_backup_count` setting.

By default, http accesses are logged just to stdout  The `log_access` setting
is a list of where http accesses are logged that can include 'screen' and
'info'.  An empty list will stop logging http accesses.

Girder logs various errors and information a different log levels.  The default
log level is 'INFO', and can be adjusted by the `log_level` setting.  Valid
choices in increasing order of verbosity include 'CRITICAL', 'ERROR',
'WARNING', 'INFO', and 'DEBUG'.  By default, when logs that are WARNING, ERROR,
or CRITICAL are sent to the error log file, and logs that are INFO or DEBUG are
sent to the info log file.  The `log_max_info_level` setting can be adjusted
to send more log messages to the info log (in addition to the error log).  For
instance, if `log_max_info_level` is set to 'CRITICAL', all messages are sent
to the info log, while the error log will just contain warnings and errors.

Setting `log_quiet` to True will suppress all output to stdout (even http
access logs if specified in `log_access`).  Information will still be sent to
the log files.

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
