.. _deploy:

Deployment Alternatives
=======================

There are many ways to deploy Girder into production. Here is a set of guides on
how to deploy Girder to several different platforms.

Reverse Proxy
-------------

In many cases, it is useful to route multiple web services from a single
server.  For example, if you have a server accepting requests at
``www.example.com``, you may want to forward requests to
``www.example.com/girder`` to a Girder instance listening on port ``9000``.

Anytime you deploy behind a proxy, Girder must be configured properly in order to serve
content correctly.  This can be accomplished by setting a few parameters in
your local configuration file (see :ref:`Configuration <configuration>`).  In this
example, we have the following:

.. code-block:: ini

    [global]
    server.socket_host = "127.0.0.1"
    server.socket_port = 9000
    tools.proxy.on = True

    [server]
    api_root = "/girder/api/v1"
    static_public_path = "/girder/static"

.. note:: If your chosen proxy server does not add the appropriate
   ``X-Forwarded-Host`` header (containing the host used in http requests,
   including any non-default port to proxied requests), the ``tools.proxy.base``
   and ``tools.proxy.local`` configuration options must also be set in the
   ``[global]`` section as:

   .. code-block:: ini

       tools.proxy.base = "http://www.example.com/girder"
       tools.proxy.local = ""

Note that after changing these parameters, it is necessary to rebuild the web client.

Nginx
+++++

Nginx can be used by adding a block such as:

.. code-block:: nginx

    location /girder/ {
        proxy_set_header Host $proxy_host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://localhost:9000/;
        # Must set the following for SSE notifications to work
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        # proxy_request_buffering option only works on nginx >= 1.7.11
        # but is necessary to support streaming requests
        proxy_request_buffering off;
    }

And under the containing ``server`` block, make sure to add the following rule:

.. code-block:: nginx

    server {
        client_max_body_size 500M;
        # ... elided configuration
    }

Ansible
-------
:doc:`deployment` provides a complete installation workflow which depends primarily on the
Ansible roles:

* `girder.girder <https://galaxy.ansible.com/girder/girder>`_
* `girder.mongodb <https://galaxy.ansible.com/girder/mongodb>`_
* `girder.nginx <https://galaxy.ansible.com/girder/nginx>`_

These roles are also independently usable and may be composed as part of larger, custom Ansible
playbooks.

Docker Container
----------------

Every time a new commit is pushed to master, Docker Hub is updated with new
images for running Girder. These containers expose Girder at
port 8080 and require the database URL to be passed in as an option. For more
information, see the
`Docker Hub Page <https://hub.docker.com/r/girder/girder>`_. Since the
container does not run a database, you'll need to run a command in the form: ::

   $ docker run -p 8080:8080 girder/girder --database mongodb://db-server-external-ip:27017/girder --host 0.0.0.0

The ``girder/girder:latest`` image is quite large and intended for use as a
base image for plugin developers. If you just need to run Girder, a slim image
based on alpine linux is provided without many of the build tools needed to
compile wheels or run girder client builds: ::

   $ docker run -p 8080:8080 girder/girder:slim --database mongodb://db-server-external-ip:27017/girder
