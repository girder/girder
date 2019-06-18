Security
========

Girder maintains data security through a variety of mechanisms.


Default Authorization
---------------------

Internally, endpoints default to requiring administrator permissions in order to
use them.  This means that, for example, when writing a plugin, a developer
must consciously choose to allow non-administrator access.  Basic
administrator, user, or token access restrictions are applied before any other
endpoint code is executed.


CORS (Cross-Origin Resource Sharing)
------------------------------------

In an out-of-the-box Girder deployment, `CORS <http://en.wikipedia.org/wiki/Cross-origin_resource_sharing>`__
is disabled for API calls. If you want your server to support API calls that are cross-origin
requests from web browsers, you'll need to modify some configuration settings.

As an administrator, go to the **Admin console**, then to **Server configuration**.
Open the **Advanced Settings** panel and you will see several settings that allow
you to specify the CORS policies for the REST API. The most important setting is the
**CORS Allowed Origins** field, which is used to specify what origins are allowed
to make cross-origin requests to the instance's REST API. By default, this is blank,
meaning no cross-origin requests are allowed. To allow requests from *any* origin,
simply set this to ``*``. You can also specify this as a comma-separated list of
explicit origins to allow. If the Origin header occurs in this explicit list, the
``Access-Control-Allow-Origin`` header of the response will be set to the request's
``Origin`` header value. You may also specify both ``*`` and a white list of explicit
origins to allow. In this case, the response header will be set to the Origin header if
it is explicitly listed, otherwise it will be set to ``*``.

If you want more fine-grained control over the CORS policies, you can also restrict
the allowed methods and allowed request headers by providing them in comma-separated
lists in the **CORS Allowed Methods** and **CORS Allowed Headers** fields, though
this is usually not necessary--the default values for these two fields are quite
permissive and should enable complete access to the web API so long as the origin
is allowed.

These settings simply control the CORS headers that are sent to the browser;
actual enforcement of the CORS policies takes place on the user's browser.

Database Injection Attacks
--------------------------

Girder defends against database injection attacks by using PyMongo as the only
pathway between the application server and the database server. This protects
against many injection vulnerabilities as described in the
`MongoDB Documentation
<http://docs.mongodb.org/manual/faq/developers/#how-does-mongodb-address-sql-or-query-injection>`__.
Girder also uses a model layer to mediate and validate all interaction with
the database. This ensures that for all database operations, structural
attributes (collection name, operation type, etc.) are hardcoded and not
modifiable by the client, while data attributes (stored content) are
validated for proper form before being accepted from a client.

Additionally, we strongly recommend configuring your MongoDB server with
JavaScript disabled unless explicitly needed for your Girder-based
application or plugin. Again, see the `MongoDB Documentation
<http://docs.mongodb.org/manual/faq/developers/#javascript>`__ for more
information.


Session Management
------------------

Girder uses session management performed through the Girder-Token header or
through a token passed through a GET parameter. This token is provided to the
client through the cookie and expires after a configurable amount of time. In
order to prevent session stealing, it is highly recommended to run Girder
under HTTPS.


Cross-Site Scripting (XSS)
--------------------------

In order to protect against XSS attacks, all input from users is sanitized
before presentation of the content on each page. This is handled by the
template system Girder uses (`Pug <https://pugjs.org/>`_). This sanitizes
user-provided content.


Cross-Site Request Forgery (CSRF)
---------------------------------

To prevent CSRF attacks, Girder requires the Girder-Token parameter as a header
for all state-changing requests. This token is taken from the user's cookie and
then passed in the request as part of the Girder one-page application and other
clients such that the cookie alone is not enough to form a valid request. A
sensible CORS policy (discussed above) also helps mitigate this attack vector.


Dependent Libraries
-------------------

Another common attack vector is through libraries upon which Girder depends
such as Cherrypy, Pug, PyMongo, etc. Girder's library dependencies reference
specific versions, ensuring that arbitrary upstream changes to libraries are
not automatically accepted into Girder's environment. Conversely, during
development and before releases we work to ensure our dependencies are up to
date in order to get the latest security fixes.


Notes on Secure Deployment
--------------------------
It is recommended that Girder be deployed using HTTPS as the only access
method. Additionally, we recommend encrypting the volume where the Mongo
database is stored as well as always connecting to Mongo using authenticated
access. The volume containing any on-disk assetstores should also be encrypted
to provide encryption of data at rest. We also recommend using a tool such as
logrotate to enable the audit of Girder logs in the event of a data breach.
Finally, we recommend a regular (and regularly tested) backup of the Girder
database, configuration, and assetstores. Disaster recovery is an important
part of any security plan.
