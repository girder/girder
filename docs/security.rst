Security
========

Girder maintains data security through a variety of mechanisms.


Default Authorization
---------------------

Internally, endpoints default to requiring adminitrator permissions in order to
use them.  This means that, for example, when writing a plugin, a developer
must consciously choose to allow non-administrator access.  Basic
administrator, user, or token access restrictions are applied before any other
enpoint code is executed.


CORS (Cross-Origin Resource Sharing)
------------------------------------

When a request is sent from a web browser that could modify the data in Girder,
the web browser sends an ``Origin`` header.  If this is not the same origin as
where a user's sessions was initiated, it is a Cross-Origin request, and is
restricted based on the Girder CORS settings.

By default, all cross-origin requests that could modify data are refused.
Different origins may be allowed via the System Configuration.  For best
security it is highly recommended that only a specific list of origins be
allowed, and not all origins using the ``*`` token.  When responding to a valid
Cross-Origin request, Girder only responds that the specific origin is allowed,
and does not reveal what other origins can be accessed.

If desired, cross-origin requests can be further restricted by specifying a
list of permitted endpoint methods.  The `CORS specification
<http://www.w3.org/TR/cors>`_ always permits ``GET``, ``HEAD``, and a subset
of ``POST`` requests.  If set in the System Configuration, other methods can be
restricted or allowed as desired.

CORS policy accepts requests with simple headers.  If requests include other
headers, they must be listed in the System Configuration, or the request will
be refused.  If the default isn't changed, Girder will authorize a small set of
headers that are typically needed when accessing the default web client from a
different origin than the Girder server.  Some configurations require
additional headers to be allowed.  For instance, if the Girder server is behind
a proxy, the ``X-Requested-With``, ``X-Forwarded-Server``, ``X-Forwarded-For``,
``X-Forwarded-Host``, and ``Remote-Addr`` headers may also be needed.  Changing
the allowed headers overrides the default values.  Therefore, to have the
default allowed headers **and** the additional headers, the allowed headers
should be changed to the combined list of the two: ::

    Accept-Encoding, Authorization, Content-Disposition, Content-Type, Cookie,
    Girder-Token, X-Requested-With, X-Forwarded-Server, X-Forwarded-For,
    X-Forwarded-Host, Remote-Addr

Although the server always allows the ``Content-Type`` header, some
cross-origin browsers may require it to be listed in the allowed headers.  If
this is the case, it muse be included in the allowed headers setting so that
browsers will be informed that it is allowed.

Girder returns an error when a Cross-Origin request is made (one with the
``Origin`` header) that does not match the system configuration settings.
Although most modern web browsers also enforce this, some additional security
is added by enforcing it at the request level.


Database Injection Attacks
--------------------------

Girder defends against database injection attacks by using PyMongo as the only
pathway between the application server and the database server. PyMongo--like
most MongoDB client libraries build up a BSON object before sending the query
to the database. This prevents most injection attacks. See the
`MongoDB Documentation
<http://docs.mongodb.org/manual/faq/developers/#how-does-mongodb-address-sql-or-query-injection>`_
for more information.

Additionally, we strongly recommend running MongoDB with JavaScript disabled
unless explicitly needed for your Girder-based application or plugin. Again,
see the `MongoDB Documentation
<http://docs.mongodb.org/manual/faq/developers/#javascript>`_
for more information.


Session Management
------------------

Girder uses session management performed through the Girder-Token header or
through a token passed through a GET parameter. This token is passed through
the cookie and expires after a configurable amount of time. In order to prevent
session stealing, it is highly recommended to run Girder under HTTPS.


Cross-Site Scripting (XSS)
--------------------------

In order to protect against XSS attacks, all input from users is sanitized
before presentation of the content on each page. This is handled by the
template system Girder uses (`Jade <http://jade-lang.com/>`_). This sanitizes
user-provided content.


Cross-Site Request Forgery (CSRF)
---------------------------------

To prevent CSRF attacks, Girder requires the Girder-Token parameter as a header
for all state-changing requests. This token is taken from the user's cookie and
then passed in the request as part of the Girder one-page application and other
clients such that the cookie alone is not enough to form a valid request. A
sensible CORS policy (discussed above) also helps mitigate this attack vector.


Dependent Libraries
------------------

Another common attack vector is through libraries upon which girder depends
such as CherryPy, Jade, PyMongo, etc. During development, and before releases
we work to ensure our dependencies are up to date in order to get the latest
security fixes.


Notes on Secure Deployment
--------------------------
It is recommended that Girder be deployed using HTTPS as the only access
method. Additionally, we recommend encrypting the volume where the Mongo
database is stored as well as always connecting to Mongo using authenticated
access. The volume containing any on-disk assetstores should also be encrypted
to provide encryption of data at rest. We also recommend using a tool such as
logrotate to enable the audit of girder logs in the event of a data breach.
Finally, we recommend a regular backup of the Girder database, configuration,
and assetstores. Disaster recovery is an important part of any security plan.
