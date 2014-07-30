.. _deploy:

Deploy
======

There are many ways to deploy Girder into production. Here is a set of guides on
how to deploy Girder to several different platforms.

Heroku
------

This guide assumes you have a Heroku account and have installed the Heroku
toolbelt.

Girder contains the requisite Procfile, buildpacks, and other configuration to
be deployed on `Heroku <http://heroku.com>`_. To deploy girder to your Heroku
space, run the following commands. We recommend doing this on your own fork of
Girder to keep any customization separate. ::

    $ cd /path/to/girder/tree
    $ heroku apps:create your_apps_name_here
    $ heroku config:add BUILDPACK_URL=https://github.com/ddollar/heroku-buildpack-multi.git
    $ heroku addons:add mongolab
    $ git remote add heroku git@heroku.com:your_apps_name_here.git
    $ git push heroku
    $ heroku open

You should now see your girder instance running on Heroku. Congratulations!

Apache Reverse Proxy
--------------------

In many cases, it is useful to route multiple web services from a single server.
You can configure Apache's `mod_proxy <http://httpd.apache.org/docs/current/mod/mod_proxy.html>`_
to route traffic to these services using a reverse proxy.  For example, if you have an
Apache server accepting requests at ``www.example.com``, and you want to forward requests
to ``www.example.com/girder`` to a Girder instance listening on port ``9000``.  You can
add the following section to your Apache config: ::

    <VirtualHost *:80>
        ProxyPass /girder http://localhost:9000
        ProxyPassReverse /girder http://localhost:9000
    </VirtualHost>

In such a scenario, Girder must be configured properly in order to serve content
correctly.  Fortunately, this can be accomplished by setting a few parameters in
your local configuration file at ``girder/conf/girder.local.cfg``.  In this example,
we have the following: ::

    [global]
    server.socket_host: "0.0.0.0"
    server.socket_port: 9000
    tools.proxy.on: True
    tools.proxy.base: "http://www.example.com/girder"
    tools.proxy.local: ""

    [server]
    api_root: "/girder/api/v1"
    static_root: "/girder/static"

After modifying the configuration, always remember to rebuild Girder by changing to
the main Girder directory and issuing the following command: ::

    $ grunt init && grunt
