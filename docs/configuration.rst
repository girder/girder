Configuration
=============

In many cases, girder will work with default configuration whether installed via
pip or from a source checkout or tarball. That said, the girder config file can
be set at the following locations (ordered by precedent):

#. The path specified by the environment variable `GIRDER_CONFIG`.
#. ~/.girder/girder.cfg
#. /etc/girder.cfg
#. /path/to/girder/package/conf/girder.local.cfg
#. /path/to/girder/package/conf/girder.dist.cfg

Logging
-------

Much of girder's ouput is placed into the error or info log file. By default,
these logs are stored in ~/.girder/logs. To set the girder log root or error and
info logs specifically, set the `log_root`, `error_log_file`, and/or
`info_log_file` variables in the `logging` config group. If `log_root` is set
error and info will be set to error.log and info.log within `log_root`
respectively. The `_log_file` variables will override that setting and are
*absolute* paths.

Plugin path
-----------
When checking out Girder from source (recommended), the plugin directory will be
set to the plugins directory by default. If Girder is installed from PyPi
(experimental), then the plugin directory can be set in the `plugin_directory`
of the `plugins` section.
