Configuration
=============

.. _configuration:

In many cases, Girder will work with default configuration whether installed via
pip or from a source checkout or tarball. To compy with 12-factor application principles, Girder settings are controlled via environment variables.

Settings
--------

Girder settings are specific key-value pairs that control system behavior.
Many of these settings can be queried or viewed using the web API endpoint at ``/api/v1/system/setting`` or via the web UI under **Admin console** -> **System configuration**.

.. _configuration_via_env:

Via the environment
...................

Any system setting can be controlled via environment variables as well. To do so, find the key of the setting and apply the following transformation:

* transform all ``.`` characters in the key to ``_``
* convert it to uppercase
* prefix it with ``GIRDER_SETTING_``

Whatever value you set for that environment variable will be parsed as JSON and used at runtime.
If the value cannot be parsed as JSON, its raw string value will be used instead. For example, to set
the setting named ``"core.brand_name"``, you'd use ``GIRDER_SETTING_CORE_BRAND_NAME='My brand name'``

Settings set through environment variables will override any setting value that is set in the database.

The full list of system settings available in Girder core can be seen in the file
``girder/girder/settings.py``, under the ``SettingKey`` class. Plugins may add additional settings
within their own packages.

Environment Variable List
.........................

This section, except for descriptions, is auto-generated from code inspection.  More descriptions will be added as users ask about settings.

.. container:: full-width-section

  .. include:: _generated_env_vars.md
     :parser: myst
