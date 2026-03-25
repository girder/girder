This is an example docker with a few inputs that uses the girder_client to fetch annotations associated with a large_image item.  It expects that you are using the girder-large-image-annotations plugin and have such annotations.

To build, use docker in this directory::

    docker build --force-rm -t girder/slicer_cli_web:girder_requests .

Altthough this can be run as a command line, it is more likely to be run from the Girder interface so that the girder-client api url and token are auto-populated.
