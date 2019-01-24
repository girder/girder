System Dependency Reference
===========================

This provides an authoritative listing of Girder's external system dependencies, for development reference.

Server Install
--------------
Installation of Girder's server has the following system dependencies:

* `Python <https://www.python.org>`_ v2.7 or v3.5+

  * This is necessary to run most of the server software.

  .. warning:: Some Girder plugins do not support Python v3 at this time due to third party library dependencies.
               Namely, the ``hdfs_assetstore`` plugin and the ``metadata_extractor`` plugin will only be available in a
               Python v2.7 environment.

  .. note:: Girder performs continuous integration testing using Python v2.7 and Python v3.5. Girder *should* work on
            newer Python v3.6+ versions as well, but that support is not verified by Girder's automated testing at this
            time, so use at your own risk.

* `pip <https://pip.pypa.io/>`_ v8.1+

  * This is necessary to install Python packages.

  * v8.1 is required to install packages via `Python wheels <https://pythonwheels.com/>`_, which significantly reduce
    system dependencies on `manylinux <https://github.com/pypa/manylinux>`_-compatible distributions (which includes
    almost everything except Alpine).

* `setuptools <https://setuptools.readthedocs.io/>`_ v21+

  * This is necessary to install Python packages.

  * v21+ is required to parse Girder's ``setup.py`` file, but the latest version can and should be installed via pip.

* A Python virtual environment (optional)

  * This is necessary to prevent conflicts with Girder's Python dependencies and allow installation as a non-root user.

  * Virtual environments are managed by the `virtualenv package <https://virtualenv.pypa.io/>`_ in Python v2.x and by
    the built-in `venv module <https://docs.python.org/3/library/venv.html>`_ in Python v3.5+.

    .. note:: Developers needing to work on several virtual environments should consider using other packages that help
              manage them such as:

              * `virtualenvwrapper <http://virtualenvwrapper.readthedocs.org/en/latest/index.html>`_

              * `autoenv <https://github.com/kennethreitz/autoenv>`_

              * `pyenv-virtualenv <https://github.com/yyuu/pyenv-virtualenv>`_

              * `pyenv-virtualenvwrapper <https://github.com/yyuu/pyenv-virtualenvwrapper>`_

* A C build environment for Python

  * This is necessary to install the `psutil <https://psutil.readthedocs.io/>`_ Python package (a requirement of
    Girder).

  * At a minimum, the environment must include GCC and the Python development headers.

.. note:: In the past, the `cryptography <https://cryptography.io/>`_ Python package (an indirect requirement of Girder)
          required OpenSSL development headers, but ``cryptography`` is now published as a Python wheel.

          In the past, the `CFFI <https://cffi.readthedocs.io/>`_ Python package (an indirect requirement of Girder)
          required ``libffi`` development headers, but ``CFFI`` is now published as a Python wheel.

Server Plugins Install
----------------------
Some of Girder's plugins require additional system dependencies, if they are installed:

* `OpenLDAP <https://www.openldap.org/>`_ v2.4.11+ development headers (for the ``ldap`` plugin)

  * This is necessary to install the `python-ldap <https://www.python-ldap.org/>`_ Python package (a requirement of the
    ``ldap`` plugin).

* `Cyrus SASL <https://www.cyrusimap.org/sasl/>`_ development headers (for the ``ldap`` plugin)

  * This is an optional dependency for installing the `python-ldap <https://www.python-ldap.org/>`_ Python package (a
    requirement of the ``ldap`` plugin).

.. note:: In the past, the `Pillow <https://pillow.readthedocs.io/>`_ Python package (a requirement of the
          ``thumbnails`` plugin ) required ``libjpeg`` and ``zlib`` development headers, but Pillow is now published as
          a Python wheel.

Server Runtime
--------------
Running Girder's server has the following additional system dependencies:

* `MongoDB <https://www.mongodb.org/>`_ v3.4+

  * This is necessary for Girder's primary application database.

  * MongoDB does not need to be installed on the same machine as Girder's server, so long as a network connection to a
    remote MongoDB is possible.

* An SMTP relay (optional)

  * This is necessary to send emails to users and administrators.

  * There are multiple web-based services that provide SMTP relays at no cost for smaller volumes of mail.

    * `Mailgun <https://www.mailgun.com/>`_ is known to work well for typical deployments.

    * `Amazon SES <https://aws.amazon.com/ses/>`_ may be simpler to manage for deployments already in AWS.

    * Any other SMTP service should be compatible, though some may only accept mail from a limited set of "From"
      addresses (which may be configured via a setting within Girder).

  * Advanced system administrators may wish to run their own SMTP server, like
    `Postfix <http://www.postfix.org/documentation.html>`_, as a relay.

    * Beware that self-hosted SMTP relays may need additional configuration with IP whitelisting, SPF, DKIM, and other
      measures before their mail can be reliably delivered to some email providers.

Web Client Build
----------------
Building Girder's web client has the following system dependencies:

* `Node.js <https://nodejs.org/>`_ v8+

  * This is necessary to execute many aspects of the web client build system.

* `npm <https://www.npmjs.com/>`_ v5.2+

  * This is necessary to install web client packages.

* `Git <https://git-scm.com/>`_

  * This is necessary to introspect Girder's install environment and generate version information as part of the web
    client build process.
