Girder: Data management platform
================================

What is Girder?
---------------

Girder is a free and open source web-based **data management platform**. What does
that mean? Girder is both a standalone application as well as a platform on top of
which new web services can be quickly and easily constructed. It's meant to be a
building block of web-based applications that have some or all of the following
requirements:

* **Data organization and dissemination**
    Many web applications need to manage data that are dynamically provided by
    users of the system, or exposed through external data services. Girder makes
    construction and organization of dynamic data hierarchies simple. One of
    the most powerful aspects of Girder is that it can transparently store, serve,
    and proxy data from heterogeneous backend storage engines through a single RESTful
    web API, including local filesystems, MongoDB databases, Amazon S3-compliant
    key-value stores, and Hadoop Distributed Filesystems (HDFS).


* **User management (authentication)**
    Girder also includes everything needed for pluggable user management and
    authentication out of the box and adheres to best practices in web security.
    The system can be configured to securely store credentials itself, or defer
    to third-party authentication services such as OAuth or LDAP.

* **Access control (authorization)**
    Girder supports a simple access control architecture that allows both user-based
    and role-based access control on resources managed in the system. The project
    has undergone rigorous security audits and has extensive automated testing
    to exercise authorization behavior and ensure correctness.

For an overview of the concepts present in Girder, we recommend checking out the :doc:`user-guide`.

Girder is published under the Apache 2.0 License. Its source code can be found at
https://github.com/girder/girder.

The architecture
----------------

As mentioned above, Girder is both a standalone application and a platform.

mention Rest API, written in python, plugin system, single-page app, etc.

.. toctree::
   :maxdepth: 2

   admin-docs
   user-docs
   developer-docs
   plugins

API Index
---------

* :ref:`genindex`
* :ref:`modindex`
