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
these logs are stored in ~/.girder/logs.
