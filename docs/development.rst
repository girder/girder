Developing Girder
=================

Girder is a platform-centric web application whose client and server are very
loosely coupled. As such, development of girder can be divided into the server
(a cherrypy-based python module) and the primary client (a backbone-based) web
client. This section is intended to get prospective contributors to understand
the tools used to develop Girder.

Server Development
------------------

Developing the server can be done...

Client Development
------------------

Coding Style
^^^^^^^^^^^^

For the JavaScript client included in Girder, we adhere to the JSLint coding
style guidelines. Though many think it is an overly-opinionated tool, we find
that such tools lend to consistent code bases. When adding a new JavaScript
file to the web client, be sure to add it to the style check listing in
`tests/clients/web/CMakeLists.txt`.
