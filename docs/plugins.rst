.. _plugins:

Plugins
=======

One of the most useful aspects of the Girder platform is its ability to be extended in
almost any way by custom plugins. Developers looking for information on writing
their own plugins should see the :ref:`Plugin Development <plugindevelopment>` section. Below is
a listing and brief documentation of some of Girder's standard plugins that come
pre-packaged with the application.

Jobs
-----------

The jobs plugin is useful for representing long-running (usually asynchronous) jobs
in the Girder data model. Since the notion of tracking batch jobs is so common to
many applications of Girder, this plugin is very generic and is meant to be an
upstream dependency of more specialized plugins that actually create and execute
the batch jobs.

The job resource that is the primary data type exposed by this plugin has many
common and useful fields, including:

- ``title``: The name that will be displayed in the job management console.
- ``type``: The type identifier for the job, used by downstream plugins opaquely.
- ``args``: Ordered arguments of the job (a list).
- ``kwargs``: Keyword arguments of the job (a dictionary).
- ``created``: Timestamp when the job was created
- ``progress``: Progress information about the job's execution.
- ``status``: The state of the job, e.g. Inactive, Running, Success.
- ``log``: Log output from this job's execution.
- ``handler``: An opaque value used by downstream plugins to identify what should
  handle this job.
- ``meta``: Any additional information about the job should be stored here by
  downstream plugins.

Jobs should be created with the ``createJob`` method of the job model. Downstream
plugins that are in charge of actually scheduling a job for execution should then
call ``scheduleJob``, which triggers the ``jobs.schedule`` event with the job
document as the event info.

For controlling what fields of a job are visible in the REST API, downstream plugins
should bind to the ``jobs.filter`` event, which receives a dictionary with ``job``
and ``user`` keys as its info. They can modify any existing fields or the job
document as needed, and can also expose or redact fields. To make some fields
visible while redacting others, you can use the event response with ``exposeFields``
and/or ``removeFields`` keys, e.g.

.. code-block:: python

  def filterJob(event):
      event.addResponse({
          'exposeFields': ['_some_other_field'],
          'removeFields': ['created']
      })

  events.bind('jobs.filter', 'a_downstream_plugin', filterJob)


Geospatial
----------

The geospatial plugin enables the storage and querying of `GeoJSON <http://geojson.org>`__
formatted geospatial data. It uses the underlying MongoDB support of geospatial
indexes and query operators to create an API for the querying of items that
either intersect a GeoJSON point, line, or polygon; are in proximity to a
GeoJSON point; or are entirely within a GeoJSON polygon or circular region. In
addition, new items may be created from GeoJSON features or feature collections.
GeoJSON properties of the features are added to the created items as metadata.

The plugin requires the `geojson <https://pypi.python.org/pypi/geojson/>`__
Python package, which may be installed using **pip**: ::

    pip install -r plugins/geospatial/requirements.txt

Once the package is installed, the plugin may be enabled via the admin console.

Google Analytics
----------------

The Google Analytics plugin enables the use of Google Analytics to track
page views with the Girder one-page application. It is primarily a client-side
plugin with the tracking ID stored in the database. Each routing change will
trigger a page view event and the hierarchy widget has special handling (though
it does not technically trigger routing events for hierarchy navigation).

To use this plugin, simply copy your tracking ID from Google Analytics into the
plugin configuration page.


Metadata Extractor
------------------

The metadata extractor plugin enables the extraction of metadata from uploaded
files such as archives, images, and videos. It may be used as either a
server-side plugin that extracts metadata on the server when a file is added
to a filesystem asset store local to the server or as a remote client that
extracts metadata from a file on a filesystem local to the client that is then
sent to the server using the Girder Python client.

The server-side plugin requires several `Hachoir <https://bitbucket.org/haypo/hachoir/wiki/Home>`_
Python packages to parse files and extract metadata from them. These packages
may be installed using **pip** as follows: ::

    pip install -r plugins/metadata_extractor/requirements.txt

Once the packages are installed, the plugin may be enabled via the admin
console on the server.

The remote client requires the same Python packages as the server plugin, but
additionally requires the `Requests <http://docs.python-requests.org/en/latest>`_ Python
package to communicate with the server using the Girder Python client. These
packages may be installed using **pip** as follows: ::

    pip install requests -r plugins/metadata_extractor/requirements.txt

Assuming ``girder_client.py`` and ``metadata_extractor.py`` are located in
the module path, the following code fragment will extract metadata from a file
located at ``path`` on the remote filesystem that has been uploaded to
``itemId`` on the server: ::

    from girder_client import GirderClient
    from metadata_extractor import ClientMetadataExtractor

    client = GirderClient(host='localhost', port=8080)
    client.authenticate(login, password)

    extractor = ClientMetadataExtractor(client, path, itemId)
    extractor.extractMetadata()

The user authenticating with ``login`` and ``password`` must have ``WRITE``
access to the file located at ``itemId`` on the server.


OAuth Login
-----------

This plugin allows users to log in using OAuth against a set of supported providers,
rather than storing their credentials in the Girder instance. Specific instructions
for each provider can be found below.

Google
******

On the plugin configuration page, you must enter a **Client ID** and **Client secret**.
Those values can be created in the Google Developer Console, in the **APIS & AUTH** >
**Credentials** section. When you create a new Client ID, you must enter the
``AUTHORIZED_JAVASCRIPT_ORIGINS`` and ``AUTHORIZED_REDIRECT_URI`` fields. These *must*
point back to your Girder instance. For example, if your Girder instance is hosted
at ``https://my.girder.com``, then you should specify the following values: ::

    AUTHORIZED_JAVASCRIPT_ORIGINS: https://my.girder.com
    AUTHORIZED_REDIRECT_URI: https://my.girder.com/api/v1/oauth/google/callback

After successfully creating the Client ID, copy and paste the client ID and client
secret values into the plugin's configuration page, and hit **Save**. Users should
then be able to log in with their Google account when they click the log in page
and select the option to log in with Google.


Provenance Tracker
------------------

The provenance tracker plugin logs changes to items and to any other resources
that have been configured in the plugin settings.  Each change record includes
a version number, the old and new values of any changed information, the ID of
the user that made the change, the current date and time, and the type of
change that occurred.

API
***

Each resource that has provenance tracking has a rest endpoint of the form
``(resource)/{id}/provenance``.  For instance, item metadata is accessible at
``item/{id}/provenance``.  Without any other parameter, the most recent change
is reported.

The ``version`` parameter can be used to get any or all provenance information
for a resource.  Every provenance record has a version number.  For each
resource, these versions start at 1.  If a positive number is specified for
``version``, the provenance record with the matching version is returned.  If a
negative number is specified, the index is relative to the end of the list of
provenance records.  That is, -1 is the most recent change, -2 the second most
recent, etc.  A ``version`` of ``all`` returns a list of all provenance records
for the resource.

All provenance records include ``version``, ``eventType`` (see below), and
``eventTime``.  If the user who authorized the action is known, their ID is
stored in ``eventUser``.

Provenance event types include:

- ``creation``: the resource was created.

- ``unknownHistory``: the resource was created when the provenance plugin was
  disabled.  Prior to this time, there is no provenance information.

- ``update``: data, metadata, or plugin-related data has changed for the
  resource.  The old values and new values of the data are recorded.  The
  ``old``  parameter contains any value that was changed (the value prior to
  the change) or has been deleted.  The ``new`` parameter contains any value
  that was changed or has been added.

- ``copy``: the resource was copied.  The original resource's provenance is
  copied to the new record, and the ``originalId`` indicates which record was
  used.

For item records, when a file belonging to that item is added, removed, or
updated, the provenance is updated with that change.  This provenance includes
a ``file`` list with the changed file(s).  Each entry in this list includes a
``fileId`` for the associated file and one of these event types:

- ``fileAdded``: a file was added to the item.  The ``new`` parameter has a
  summary of the file information, including its assetstore ID and value used
  to reference it within that assetstore.

- ``fileUpdate``: a file's name or other data has changed, or the contents of
  the file were replaced.  The ``new`` and ``old`` parameters contain the data
  values that were modified, deleted, or added.

- ``fileRemoved``: a file was removed from the item.  The ``old`` parameter has
  a summary of the file information.  If this was the only item using this file
  data, the file is removed from the assetstore.

Gravatar Portraits
------------------

This lightweight plugin makes all users' Gravatar image URLs available for use
in clients. When enabled, user documents sent through the REST API will contain
a new field ``gravatar_baseUrl`` if the value has been computed. If that field
is not set on the user document, instead use the URL ``/user/:id/gravatar`` under
the Girder API, which will compute and store the correct Gravatar URL, and then
redirect to it. The next time that user document is sent over the REST API,
it should contain the computed ``gravatar_baseUrl`` field.

Javascript clients
******************

The Gravatar plugin's javascript code extends the Girder web client's ``girder.models.UserModel``
by adding the ``getGravatarUrl(size)`` method that adheres to the above behavior
internally. You can use it on any user model with the ``_id`` field set, as in the following example:

.. code-block:: javascript

    if (girder.currentUser) {
        this.$('div.gravatar-portrait').css(
            'background-image', 'url(' +
            girder.currentUser.getGravatarUrl(36) + ')');
    }

.. note:: Gravatar images are always square; the ``size`` parameter refers to
   the side length of the desired image in pixels.
