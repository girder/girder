Configuration
=============

.. _configuration:

In many cases, Girder will work with default configuration whether installed via
pip or from a source checkout or tarball. That said, the Girder config file can
be set at the following locations (ordered by precedent):

#. The path specified by the environment variable ``GIRDER_CONFIG``.
#. ~/.girder/girder.cfg
#. /etc/girder.cfg

Settings
--------

Girder settings are specific key-value pairs that control system behavior.
There are two ways to change Girder settings.

Via the Web API / front-end web site
....................................

System settings can be set and retrieved using the web API endpoint at ``/api/v1/system/setting``.
Most of them are exposed via the web UI under **Admin console** -> **System configuration**.
When setting the values through the web API endpoint, they will be interpreted as JSON.

.. note:: Modifying setting values via the web API is officially deprecated, as it violates the
   `Twelve-Factor App <https://12factor.net/>`_  principle of storing configuration in the
   environment. Setting values should instead be set via environment variables as documented below.

Via the environment
...................

Any system setting can be controlled via environment variables as well. To do so, find the
key of the setting and apply the following transformation:

* transform all ``.`` characters in the key to ``_``
* convert it to uppercase
* prefix it with ``GIRDER_SETTING_``

Whatever value you set for that environment variable will be parsed as JSON and used at runtime.
If the value cannot be parsed as JSON, its raw string value will be used instead. For example, to set
the setting named ``"core.brand_name"``, you'd use ``GIRDER_SETTING_CORE_BRAND_NAME='My brand name'``

Settings set through environment variables will override any setting value that is set in the database
via the web API.

The full list of system settings available in Girder core can be seen in the file
``girder/girder/settings.py``, under the ``SettingKey`` class. Plugins may add additional settings
within their own packages.

Logging
-------

Much of Girder's output is placed into the error or info log file. By default,
these logs are stored in ~/.girder/logs. To set the Girder log root or error and
info logs specifically, set the ``log_root``, ``error_log_file``, and/or
``info_log_file`` variables in the ``logging`` config group. If ``log_root`` is set,
error and info will be set to error.log and info.log within ``log_root``
respectively. The ``_log_file`` variables will override that setting and are
*absolute* paths.

Log files are written to until they reach a specified size.  They are then
rotated, keeping a number of files before the oldest file is deleted.  The size
of the files can be set via the ``log_max_size`` setting.  This is either an
integer value in bytes or a string with a integer value followed by a 'kb',
'Mb', or 'Gb' suffix.  The number of files can be adjusted using the
``log_backup_count`` setting.

By default, http accesses are logged just to stdout  The ``log_access`` setting
is a list of where http accesses are logged that can include 'screen' and
'info'.  An empty list will stop logging http accesses.

Girder logs various errors and information a different log levels.  The default
log level is 'INFO', and can be adjusted by the ``log_level`` setting.  Valid
choices in increasing order of verbosity include 'CRITICAL', 'ERROR',
'WARNING', 'INFO', and 'DEBUG'.  By default, when logs that are WARNING, ERROR,
or CRITICAL are sent to the error log file, and logs that are INFO or DEBUG are
sent to the info log file.  The ``log_max_info_level`` setting can be adjusted
to send more log messages to the info log (in addition to the error log).  For
instance, if ``log_max_info_level`` is set to 'CRITICAL', all messages are sent
to the info log, while the error log will just contain warnings and errors.

Setting ``log_quiet`` to True will suppress all output to stdout (even http
access logs if specified in ``log_access``).  Information will still be sent to
the log files.
