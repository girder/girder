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
be deployed on `Heroku <https://www.heroku.com>`_. To deploy Girder to your Heroku
space, run the following commands. We recommend doing this on your own fork of
Girder to keep any customization separate. ::

    $ cd /path/to/girder/tree
    $ heroku apps:create your_apps_name_here
    $ heroku config:add BUILDPACK_URL=https://github.com/ddollar/heroku-buildpack-multi.git
    $ heroku addons:add mongolab
    $ git remote add heroku git@heroku.com:your_apps_name_here.git
    $ git push heroku
    $ heroku open

You should now see your Girder instance running on Heroku. Congratulations!

Reverse Proxy
-------------

In many cases, it is useful to route multiple web services from a single
server.  For example, if you have a server accepting requests at
``www.example.com``, you may want to forward requests to
``www.example.com/girder`` to a Girder instance listening on port ``9000``.

Apache
++++++

When using Apache, configure Apache's `mod_proxy
<http://httpd.apache.org/docs/current/mod/mod_proxy.html>`_ to route traffic to
these services using a reverse proxy.  Add the following section to your Apache
config:

.. code-block:: apacheconf

    <VirtualHost *:80>
        ProxyPass /girder http://localhost:9000
        ProxyPassReverse /girder http://localhost:9000
    </VirtualHost>

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
        ...
    }

Girder Settings
+++++++++++++++

In such a scenario, Girder must be configured properly in order to serve
content correctly.  This can be accomplished by setting a few parameters in
your local configuration file at ``girder/conf/girder.local.cfg``.  In this
example, we have the following:

.. code-block:: ini

    [global]
    server.socket_host: "0.0.0.0"
    server.socket_port: 9000
    tools.proxy.on: True

    [server]
    api_root: "/girder/api/v1"
    static_root: "/girder/static"

.. note:: If your chosen proxy server does not add the appropriate
   ``X-Forwarded-Host`` header (containing the host used in http requests,
   including any non-default port to proxied requests), the ``tools.proxy.base``
   and ``tools.proxy.local`` configuration options must also be set in the
   ``[global]`` section as:

   .. code-block:: ini

       tools.proxy.base: "http://www.example.com/girder"
       tools.proxy.local: ""

After modifying the configuration, always remember to rebuild Girder by
changing to the Girder directory and issuing the following command: ::

    $ npm install

Docker Container
----------------

Every time a new commit is pushed to master, Docker Hub is updated with a new
image of a docker container running Girder. This container exposes Girder at
port 8080 and requires the database URL to be passed in as an option. For more
information, see the
`Docker Hub Page <https://registry.hub.docker.com/u/girder/girder/>`_. Since the
container does not run a database, you'll need to run a command in the form: ::

   $ docker run -p 8080:8080 girder/girder -d mongodb://db-server-external-ip:27017/girder

Google Container Engine
-----------------------

Google Container Engine lets you host and manage Docker containers on Google
Compute Engine instances. Before following the instructions here, follow
Google's tutorial for setting up
`Wordpress <https://cloud.google.com/container-engine/docs/hello-wordpress>`_,
which will make the following steps more clear.

We will assume you have performed ``gcloud auth login`` and
the following environment variables set: ::

    $ export ZONE=us-central1-a
    $ export CLUSTER_NAME=hello-girder

Start a new project in Google Developers Console
(here we assume its identifier is ``my-girder``).
Set this as your active project with ::

    $ gcloud config set project my-girder

Now click the Container Engine menu item on the left of the console
to initialize the container service, then create a new cluster with: ::

    $ gcloud preview container clusters create $CLUSTER_NAME --num-nodes 1 --machine-type n1-standard-2 --zone $ZONE

This will create two instances, a master and a worker: ::

    $ gcloud compute instances list --zone $ZONE
    NAME                    ZONE          MACHINE_TYPE  INTERNAL_IP   EXTERNAL_IP    STATUS
    k8s-hello-girder-master us-central1-a n1-standard-2 X.X.X.X       X.X.X.X        RUNNING
    k8s-hello-girder-node-1 us-central1-a n1-standard-2 X.X.X.X       X.X.X.X        RUNNING

The worker will hold
our Docker containers, MongoDB and Girder. The worker needs some extra storage
than the standard 10GB, so let's make a new 100GB storage drive and attach it
to our worker: ::

    $ gcloud compute disks create mongodb --size 100GB --zone $ZONE
    $ gcloud compute instances attach-disk k8s-hello-girder-node-1 --disk mongodb --zone $ZONE

Now we need to ssh into our worker node, which you can do from the Developers Console,
and mount the disk to ``/data``. First we find the name of the device, here ``sdb``. ::

    user_name@k8s-hello-girder-node-1:~$ ls -l /dev/disk/by-id/google-*
    lrwxrwxrwx 1 root root  9 Nov 22 20:31 /dev/disk/by-id/google-mongodb -> ../../sdb
    lrwxrwxrwx 1 root root  9 Nov 22 19:32 /dev/disk/by-id/google-persistent-disk-0 -> ../../sda
    lrwxrwxrwx 1 root root 10 Nov 22 19:32 /dev/disk/by-id/google-persistent-disk-0-part1 -> ../../sda1

Then we create the directory and mount the drive: ::

    user_name@k8s-hello-girder-node-1:~$ sudo mkdir /data
    user_name@k8s-hello-girder-node-1:~$ sudo /usr/share/google/safe_format_and_mount -m "mkfs.ext4 -F" /dev/sdb /data

Now we are ready to install our pod, which is a collection of containers that
work together. Save the following yaml specification for our MongoDB/Girder pod
to ``pod.yaml``:

.. code-block:: yaml

    ---
        version: v1beta1
        id: girder
        kind: Pod
        desiredState:
            manifest:
                version: v1beta2
                containers:
                  -
                    name: mongodb
                    image: dockerfile/mongodb
                    ports:
                      -
                        name: db
                        containerPort: 27017
                    volumeMounts:
                      -
                        name: data
                        mountPath: /data/db
                  -
                    name: application
                    image: girder/girder
                    ports:
                      -
                        name: app
                        containerPort: 8080
                        hostPort: 80
                volumes:
                  -
                    name: data
                    source:
                        hostDir:
                            path: /data/db

Note that we are letting MongoDB use the host's ``/data`` directory,
which will have more space and will persist even if our containers
are shut down and restarted. Start the pod back at your local
command line with: ::

    $ gcloud preview container pods --cluster-name $CLUSTER_NAME create girder --zone $ZONE --config-file pod.yaml

You can check the status of your pod with: ::

    $ gcloud preview container pods --cluster-name $CLUSTER_NAME describe girder --zone $ZONE
    ID          Image(s)                          Host                                                     Labels      Status
    ----------  ----------                        ----------                                               ----------  ----------
    girder      dockerfile/mongodb,girder/girder  k8s-hello-girder-node-1.c.hello-girder.internal/X.X.X.X              Running

Add a firewall rule to expose port 80 on your worker: ::

    $ gcloud compute firewall-rules create hello-girder-node-80 --allow tcp:80 --target-tags k8s-hello-girder-node

After everything starts, which may take a few minutes, you should be able
to visit your Girder instance at ``http://X.X.X.X`` where ``X.X.X.X`` is the
IP address in the container description above. Congratulations, you
have a full Girder instance available on Google Container Engine!
