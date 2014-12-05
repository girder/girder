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

When a request is sent from a web browser that could modify the data in girder,
the web browser sends an ``Origin`` header.  If this is not the same origin as
where a user's sessions was initiated, it is a Cross-Origin request, and is
restricted based on the girder CORS settings.

By default, all cross-origin requests that could modify data are refused.
Different origins may be allowed via the System Configuration.  For best
security is recommended that only a specific list of origins be allowed, and
not all origins using the ``*`` token.  When responding to a valid Cross-Origin
request, Girder only responds that the specific origin is allowed, and does not
reveal what other origins can be accessed.

If desired, cross-origin requests can be further restricted by specifying a
list of permitted endpoint methods.  The ``CORS specification
<http://www.w3.org/TR/cors>``_ always permits ``GET``, ``HEAD``, and a subset
of ``POST`` requests.  If set in the System Configuration, other methods can be
restricted or allowed as desired.

CORS policy accepts requests with simple headers.  If requests include other
headers, they must be listed in the System Configuration, or the request will
be refused.

Girder returns an error when a Cross-Origin request is made (one with the
``Origin`` header) that does not match the system configuration settings.
Although most modern web browsers also enforce this, some additional security
is added by enforcing it at the request level.
