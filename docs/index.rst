Girder: a data management platform
==================================

|build-status| |license-badge| |codecov-badge| |github-badge|

.. |build-status| image:: https://circleci.com/gh/girder/girder.png?style=shield
    :target: https://circleci.com/gh/girder/girder
    :alt: Build Status

.. |license-badge| image:: https://raw.githubusercontent.com/girder/girder/master/docs/license.png
    :target: https://pypi.python.org/pypi/girder
    :alt: License

.. |codecov-badge| image:: https://img.shields.io/codecov/c/github/girder/girder.svg
    :target: https://codecov.io/gh/girder/girder
    :alt: Coverage Status

.. |github-badge| image:: https://img.shields.io/github/stars/girder/girder.svg?style=social&label=GitHub
    :target: https://github.com/girder/girder
    :alt: GitHub


What is Girder?
---------------

Girder is a free and open source web-based **data management platform**, developed by
`Kitware <http://www.kitware.com/>`_. What does
that mean? Girder is both a standalone application and a platform for building new web
services. It's meant to enable quick and easy construction of web applications
that have some or all of the following requirements:

* **Data organization and dissemination**
    Many web applications need to manage data that are dynamically provided by
    users of the system, or exposed through external data services. Girder makes
    construction and organization of dynamic data hierarchies simple. One of
    the most powerful aspects of Girder is that it can transparently store, serve,
    and proxy data from heterogeneous backend storage engines through a single RESTful
    web API, including local filesystems, MongoDB databases, Amazon S3-compliant
    key-value stores, and Hadoop Distributed Filesystems (HDFS).

* **User management & authentication**
    Girder also includes everything needed for pluggable user management and
    authentication out of the box and adheres to best practices in web security.
    The system can be configured to securely store credentials itself, or defer
    to third-party authentication services such as OAuth or LDAP.

* **Authorization management**
    Girder supports a simple access control scheme that allows both user-based
    and role-based access control on resources managed in the system. The project
    has undergone rigorous security audits and has extensive automated testing
    to exercise authorization behavior and ensure correctness.

For an overview of the concepts present in Girder, we recommend checking out the :doc:`user-guide`.

Girder is published under the Apache 2.0 License. Its source code can be found at
https://github.com/girder/girder.

The architecture
----------------

Girder's server-side architecture is focused around the construction of RESTful
web APIs to afford minimal coupling between the backend services and the
frontend clients. This decoupling allows multiple clients all to use the same
server-side interface. While Girder does contain its own single-page javascript
web application, the system can be used by any HTTP-capable client, either inside
or outside of the web browser environment. Girder can even be run without its
front-end application present at all, only serving the web API routes.

The web API is mostly used to interact with resources that are represented by **models**
in the system. Models internally interact with a Mongo database to store and
retrieve persistent records. The models contain methods for creating, changing,
retrieving, and deleting those records. The core Girder model
types are described in the :ref:`concepts` section of the user guide.

The primary method of customizing and extending Girder is via the development of
**plugins**, the process of which is described in the :doc:`plugin-development`
section of this documentation. Plugins can, for example, add new REST routes,
modify or remove existing ones, serve up a different web application from the server
root, hook into model lifecycle events or specific API calls, override authentication
behavior to support new authentication services or protocols, add a new backend
storage engine for file storage, or even interact with a completely different DBMS
to persist system records -- the extent to which plugins are allowed to modify and
extend the core system behavior is nearly limitless.

Plugins are self-contained in their own directory within the Girder source tree.
Therefore they can reside in their own separate source repository, and are installed
by simply copying the plugin source tree under an existing Girder installation's
``plugins`` directory. The Girder repository contains several generally
useful plugins out of the box, which are described in the :doc:`plugins` section.


Table of contents
-----------------

.. toctree::
   :maxdepth: 2

   admin-docs
   user-docs
   developer-docs
   plugins
   changelog

API index
---------

* :ref:`genindex`
* :ref:`modindex`
