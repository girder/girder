API Documentation
=================

.. _restapi:

RESTful API
-----------

Clients access Girder servers uniformly via its RESTful web API. By providing
a single, stable, consistent web API, it is possible to write multiple
interchangeable clients using different technologies.

When a Girder instance is deployed, it typically also serves a page
that uses `Swagger <https://swagger.io>`_ to document
all available RESTful endpoints in the web API and also provide an easy way
for users to execute those endpoints with parameters of their choosing. In
this way, the Swagger page is just the simplest and lightest client application
for Girder. This page is served out of the path ``/api`` under the root path of
your Girder instance.


Internal Python API
-------------------

.. _models:

Models
^^^^^^

In Girder, the model layer is responsible for actually interacting with the
underlying database. Model classes are where the documents representing
resources are actually saved, retrieved, and deleted from the DBMS. Validation
of the resource documents is also done in the model layer, and is invoked
each time a document is about to be saved.

Typically, there is a model class for each resource type in the system. These
models are loaded as singletons for efficiency, but you should use them like
normal objects. For example, to use the ``list`` method of the Group model:

.. code-block:: python

    from girder.models.group import Group
    groups = Group().list(user=self.getCurrentUser())

All models that require the standard access control semantics should extend the
`AccessControlledModel` class. Otherwise, they should extend the `Model` class.

All model classes must have an ``initialize`` method in which they declare
the name of their corresponding Mongo collection, as well as any collection
indexes they require. For example, to make a model whose documents live in a
collection called ``cat_collection`` and ensure that the ``name`` key is indexed
on that collection, you would use the following ``initialize`` method:

.. code-block:: python

    from girder.models.model_base import Model

    class Cat(Model):
        def initialize(self):
            self.name = 'cat_collection'
            self.ensureIndex('name')


Model Helper Functions
~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: girder.models
   :members:

Model Base
~~~~~~~~~~
.. automodule:: girder.models.model_base
   :members:

API Key
~~~~~~~
.. automodule:: girder.models.api_key
   :members:

User
~~~~
.. automodule:: girder.models.user
   :members:

Token
~~~~~
.. automodule:: girder.models.token
   :members:

Group
~~~~~
.. automodule:: girder.models.group
   :members:

Collection
~~~~~~~~~~

.. automodule:: girder.models.collection
   :members:

Folder
~~~~~~
.. automodule:: girder.models.folder
   :members:

Item
~~~~
.. automodule:: girder.models.item
   :members:

Setting
~~~~~~~

.. automodule:: girder.models.setting
   :members:

Assetstore
~~~~~~~~~~

.. automodule:: girder.models.assetstore
   :members:

File
~~~~

.. automodule:: girder.models.file
   :members:

Upload
~~~~~~

.. automodule:: girder.models.upload
   :members:

Notification
~~~~~~~~~~~~

.. automodule:: girder.models.notification
    :members:

Web API Endpoints
^^^^^^^^^^^^^^^^^

Base Classes and Helpers
~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: girder.api.access
   :members:

.. automodule:: girder.api.api_main
   :members:

.. automodule:: girder.api.describe
   :members:

.. automodule:: girder.api.docs
   :members:

.. automodule:: girder.api.filter_logging
   :members:

.. automodule:: girder.api.rest
   :members:

.. _api-docs-utility:

Utility
^^^^^^^
.. automodule:: girder.utility
   :members:

.. automodule:: girder.utility.abstract_assetstore_adapter
   :members:

.. automodule:: girder.utility.acl_mixin
   :members:

.. automodule:: girder.utility.assetstore_utilities
   :members:

.. automodule:: girder.utility.config
   :members:

.. automodule:: girder.utility.filesystem_assetstore_adapter
   :members:

.. automodule:: girder.utility.gridfs_assetstore_adapter
   :members:

.. automodule:: girder.utility.mail_utils
   :members:

.. automodule:: girder.utility.model_importer
   :members:

.. automodule:: girder.utility.path
   :members:

.. automodule:: girder.utility.progress
   :members:

.. automodule:: girder.utility.resource
   :members:

.. automodule:: girder.utility.s3_assetstore_adapter
   :members:

.. automodule:: girder.utility.search
   :members:

.. automodule:: girder.utility.server
   :members:

.. automodule:: girder.utility.setting_utilities
   :members:

.. automodule:: girder.utility.system
   :members:

.. automodule:: girder.utility.webroot
   :members:

.. automodule:: girder.utility.ziputil
   :members:

Constants
~~~~~~~~~
.. automodule:: girder.constants
   :members:

.. _events:

Events
~~~~~~
.. automodule:: girder.events
    :members:

Exceptions
~~~~~~~~~~
.. automodule:: girder.exceptions
   :members:

Logging
~~~~~~~
.. automodule:: girder
   :members:

Plugins
~~~~~~~
.. automodule:: girder.plugin
   :members:

Python Client
-------------

See :ref:`python-client`

Web client
----------

Documentation for Girder's web client library is built and hosted by esdoc and can be found
`here <https://doc.esdoc.org/github.com/girder/girder>`_.
