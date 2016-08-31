API Documentation
=================

.. _restapi:

RESTful API
-----------

Clients access Girder servers uniformly via its RESTful web API. By providing
a single, stable, consistent web API, it is possible to write multiple
interchangeable clients using different technologies.

When a Girder instance is deployed, it typically also serves a page
that uses `Swagger <https://helloreverb.com/developers/swagger>`_ to document
all available RESTful endpoints in the web API and also provide an easy way
for users to execute those endpoints with parameters of their choosing. In
this way, the Swagger page is just the simplest and lightest client application
for Girder. This page is served out of the path ``/api`` under the root path of
your Girder instance.

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
is the name of the model.  For example: ::

    groups = self.model('group').list(user=self.getCurrentUser())

All models that require the standard access control semantics should extend the
`AccessControlledModel` class. Otherwise, they
should extend the `Model` class.

All model classes must have an ``initialize`` method in which they declare
the name of their corresponding Mongo collection, as well as any collection
indices they require. For example: ::

    from girder.models.model_base import Model

    class Cat(Model):
        def initialize(self):
            self.name = 'cat_collection'

The above model singleton could then be accessed via: ::

    self.model('cat')

If you wish to use models in something other than a REST Resource or Model,
either mixin or instantiate the `ModelImporter` class.

Model Helper Functions
^^^^^^^^^^^^^^^^^^^^^^
.. automodule:: girder.models
   :members:

Model Base
^^^^^^^^^^
.. automodule:: girder.models.model_base
   :members:

User
^^^^
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

Assetstore
^^^^^^^^^^

.. automodule:: girder.models.assetstore
   :members:

File
^^^^

.. automodule:: girder.models.file
   :members:

Upload
^^^^^^

.. automodule:: girder.models.upload
   :members:

.. _events:

Events
^^^^^^

.. automodule:: girder.events
    :members:

Notification
^^^^^^^^^^^^

.. automodule:: girder.models.notification
    :members:

Python API for RESTful web API
------------------------------

Base Classes and Helpers
^^^^^^^^^^^^^^^^^^^^^^^^
.. automodule:: girder.api.describe
   :members:

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

.. automodule:: girder.utility.progress
   :members:

.. automodule:: girder.utility.path
   :members:

Constants
---------
.. automodule:: girder.constants
   :members:

Clients
-------

jQuery Plugins
^^^^^^^^^^^^^^

There are a set of jQuery plugins that interact with the Girder API. These can
be found in the ``clients/jquery`` directory of the source tree.


.. js:function:: $.girderBrowser(cfg)

    :param object cfg: Configuration object

    :param boolean caret: Draw a caret on main menu to indicate dropdown (`true` by
        default).

    :param string label: The text to display in the main menu dropdown.

    :param string api: The root path to the Girder API (`/api/v1` by default).

    :param function(item,api) selectItem: A function to call when an item is
        clicked.  It will be passed the item's information and the API root.

    :param function(folder,api) selectFolder: A function to call when a folder
        is clicked.  It will be passed the folder's information and the API root.

    :param boolean search: Include a search box for gathering general string
        search results.

    :param function(result,api) selectSearchResult: A function to call when a
        search result is clicked.  It will be passed the result item's information
        and the API root.

This plugin creates a Bootstrap dropdown menu reflecting the current contents of
a Girder server as accessible by the logged-in user.  The selection on which
this plugin is invoked should be an ``<li>`` element that is part of a Bootstrap
navbar.  For example:

.. code-block:: html

    <div class="navbar navbar-default navbar-fixed-top">
        <div class=navbar-header>
            <a class=navbar-brand href=/examples>Girder</a>
        </div>

        <ul class="nav navbar-nav">
            <li id=girder-browser>
                <a>Dummy</a>
            </li>
        </ul>
    </div>

Then, in a JavaScript file:

.. code-block:: javascript

    $("#girder-browser").girderBrowser({
        // Config options here
        //     .
        //     .
        //     .
    });

The anchor text "dummy" in the example HTML will appear in the rendered page if
the plugin fails to execute for any reason.  This is purely a debugging measure
- since the plugin empties the target element before it creates the menu, the
anchor tag (or any other content) is not required.
