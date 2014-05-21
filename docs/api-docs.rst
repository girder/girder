API Documentation
=================

.. _models:

Models
------

In Girder, the model layer is responsible for actually interacting with the
underlying database. Model classes are where the documents representing
resources are actually saved, retrieved, and deleted from the DBMS. Validation
of the resource documents is also done in the model layer, and is invoked
each time a document is about to be saved.

Typically, there is a model class for each resource type in the system. These
models are loaded as singletons for efficiency, and can be accessed in
REST resources or other models by invoking ``self.model('foo')``, where ``foo``
is the name of the model.  For example, ::

    groups = self.model('group').list(user=self.getCurrentUser())

All models that require the standard access control semantics should extend the
:ref:`AccessControlledModel` class. Otherwise, they
should extend the :ref:`Model` class.

All model classes must have an ``initialize`` method in which they declare
the name of their corresponding Mongo collection, as well as any collection
indices they require. For example, ::

    from girder.models.model_base import Model

    class Cat(Model):
        def initialize(self):
            self.name = 'cat_collection'

The above model singleton could then be accessed via ::

    self.model('cat')

If you wish to use models in something other than a REST Resource or Model,
either mixin or instantiate the :ref:`ModelImporter` class.

Model Helper Functions
^^^^^^^^^^^^^^^^^^^^^^
.. automodule:: girder.models
   :members:

Model Base
^^^^^^^^^^
.. automodule:: girder.models.model_base
   :members:

.. _events:

Events
^^^^^^

.. automodule:: girder.events
    :members:

User
^^^^^
.. automodule:: girder.models.user
   :members:

Password
^^^^^^^^
.. automodule:: girder.models.password
   :members:

Token
^^^^^
.. automodule:: girder.models.token
   :members:

Group
^^^^^
.. automodule:: girder.models.group
   :members:

Collection
^^^^^^^^^^

.. automodule:: girder.models.collection
   :members:

Folder
^^^^^^
.. automodule:: girder.models.folder
   :members:

Item
^^^^
.. automodule:: girder.models.item
   :members:

Setting
^^^^^^^

.. automodule:: girder.models.setting
   :members:

Web API Endpoints
-----------------

Base Classes and Helpers
^^^^^^^^^^^^^^^^^^^^^^^^
.. automodule:: girder.api.api_main
   :members:

.. automodule:: girder.api.rest
   :members:

User
^^^^
.. automodule:: girder.api.v1.user
   :members:

Group
^^^^^
.. automodule:: girder.api.v1.group
   :members:

Item
^^^^
.. automodule:: girder.api.v1.item
   :members:

Folder
^^^^^^
.. automodule:: girder.api.v1.folder
   :members:

.. _api-docs-utility:

Utility
-------
.. automodule:: girder.utility.model_importer
   :members:

.. automodule:: girder.utility.server
   :members:

.. automodule:: girder.utility.config
   :members:

.. automodule:: girder.utility.mail_utils
   :members:

Constants
---------
.. automodule:: girder.constants
   :members:
