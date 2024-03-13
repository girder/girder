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



.. _configuration_via_env:

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
