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
