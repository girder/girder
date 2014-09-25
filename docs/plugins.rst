.. _plugins:

Plugins
=======

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

Geospatial
----------

The geospatial plugin enables the storage and querying of `GeoJSON <http://geojson.org>`_
formatted geospatial data. It uses the underlying MongoDB support of geospatial
indexes and query operators to create an API for the querying of items that
either intersect a GeoJSON point, line, or polygon; are in proximity to a
GeoJSON point; or are entirely within a GeoJSON polygon or circular region. In
addition, new items may be created from GeoJSON features or feature collections.
GeoJSON properties of the features are added to the created items as metadata.

The plugin requires the `geojson <https://pypi.python.org/pypi/geojson/>`_
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

Assuming ``GirderClient.py`` and ``metadata_extractor.py`` are located in
the module path, the following code fragment will extract metadata from a file
located at ``path`` on the remote filesystem that has been uploaded to
``itemId`` on the server: ::

    from GirderClient import GirderClient
    from metadata_extractor import ClientMetadataExtractor

    client = GirderClient(host='localhost', port=8080)
    client.authenticate(login, password)

    extractor = ClientMetadataExtractor(client, path, itemId)
    extractor.extractMetadata()

The user authenticating with ``login`` and ``password`` must have ``WRITE``
access to the file located at ``itemId`` on the server.
