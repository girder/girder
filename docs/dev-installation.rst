Developer Installation
======================

It is recommended to use ``docker-compose up`` to run Girder in development.

If you wish to run Girder natively, you'll need to run your own ``mongod``, and run: ::

    girder serve

This command runs a local development server on port 8080, but is not suitable
for production deployments.
