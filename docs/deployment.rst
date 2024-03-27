.. _deployment:

Deployment
==========

Girder exposes a well-behaved WSGI application at ``girder.wsgi:app``, so it can be deployed behind
any WSGI server. There are many servers and managed cloud offerings that will run WSGI applications,
and we won't attempt to enumerate them all. We like ``gunicorn``, so we provide an example of a
simple invocation that serves Girder: ::

    gunicorn girder.wsgi:app --bind=localhost:8080 --workers=4 --preload

Because deployment requirements are very specific to each application, we consider configuration
and tuning of the WSGI server to be out of scope of Girder's documentation.

A note on reverse proxy configuration
-------------------------------------

Typically, one would serve Girder behind a reverse proxy that manages things like TLS termination.
If you're setting up your own proxy rather than using a managed cloud offering, you will need to
configure it to support Girder's behaviors, in particular for large file uploads and downloads.
We provide an example nginx configuration block to show the settings that are necessary for Girder
to work properly behind nginx:

.. code-block:: nginx

    location / {
        proxy_set_header Host $proxy_host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://localhost:8080/;
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
    }
