Installation Guide
==================


To install the Girder distribution from the python package index, simply run ::

    pip install girder

This will install the core Girder server as a site package in your system
or virtual environment. At this point, you might want to check the
:doc:`configuration <configuration>` to change your plugin and logging
paths.  In order to use the web interface, you must also install the web client
libraries. Girder installs a python script that will automatically build and
install these libraries for you. Just run the following command: ::

   girder-install web

.. note:: Installing the web client code requires the node package manager (npm).
   See the :doc:`prerequisites` section for instructions on installing nodejs.

.. note:: If you installed Girder into your system ``site-packages``, you may
   need to run the above commands as root.

Once this is done, you are ready to start using Girder as described in this
section: :ref:`run-girder`.

