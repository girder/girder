Tutorials
=========


# TODO(zach) move the following section somewhere useful

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
`plugins` directory. The Girder repository contains several generally
useful plugins out of the box, which are described in the :doc:`plugins` section.
