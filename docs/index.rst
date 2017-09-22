Girder: a data management platform
==================================

|build-status| |license-badge| |gitter-badge| |codecov-badge| |github-badge|

.. |build-status| image:: https://circleci.com/gh/girder/girder.png?style=shield
    :target: https://circleci.com/gh/girder/girder
    :alt: Build Status

.. |license-badge| image:: https://raw.githubusercontent.com/girder/girder/master/docs/license.png
    :target: https://pypi.python.org/pypi/girder
    :alt: License

.. |gitter-badge| image:: https://badges.gitter.im/Join Chat.svg
    :target: https://gitter.im/girder/girder?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
    :alt: Gitter Chat

.. |codecov-badge| image:: https://img.shields.io/codecov/c/github/girder/girder.svg
    :target: https://codecov.io/gh/girder/girder
    :alt: Coverage Status

.. |github-badge| image:: https://img.shields.io/github/stars/girder/girder.svg?style=social&label=GitHub
    :target: https://github.com/girder/girder
    :alt: GitHub

What is Girder?
---------------

Girder is a libre open source web-based **data management platform** developed by
`Kitware <http://www.kitware.com/>`_ as part of the
`Resonant data and analytics ecosystem <http://resonant.kitware.com/>`_. What does
that mean? Girder is both a standalone application and a platform for building new web
services.

For an overview of the concepts present in Girder, we recommend checking out the :doc:`user-guide`.

Why Girder?
-----------

Girder as a platform is meant to enable quick and easy construction of web applications
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
    to third-party authentication services such as OAuth or LDAP/Active Directory.

* **Authorization management**
    Girder supports a simple access control scheme that allows both user-based
    and role-based access control on resources managed in the system. The project
    has undergone rigorous security audits and has extensive automated testing
    to exercise authorization behavior and ensure correctness.

* **Offline analytics / data processing**
    Many users of Girders also deploy its companion offline processing tool,
    `Girder Worker <http://girder-worker.readthedocs.io/en/latest/>`_. Using the worker,
    you can run batch analytics on data hosted in Girder using python scripts
    or arbitrary Docker images, with real-time job monitoring, logging, and statistics
    integrated into the Girder interface.

Its true value, though, is in **extensibility and flexibility**; its plugin system provides
almost unlimited power to add new capabilities to the system, or alter existing mechanisms
through easy-to-use modes of extension, which are documented in our various :doc:`tutorials`.

Organization of these docs
--------------------------

These docs are roughly divided by intended task and target audience.

* If you are a **Developer** wanting to build your own Girder plugins, you should start by
  following the :doc:`dev-installation`. After you get you development environment
  set up, browse the :doc:`tutorials` to learn about and see examples of common patterns
  of how to extend and modify the Girder platform to meet your specific needs.
* If you are an **Administrator** attempting to deploy your own instance of Girder into
  production, check out the :doc:`deploy`.
* If you are a **User** of Girder and just want to learn about the fundamentals of the
  system and how to use it, check out the :doc:`user-guide`.


Table of contents
-----------------

.. toctree::
   :maxdepth: 2

   installation
   user-guide
   developer-docs
