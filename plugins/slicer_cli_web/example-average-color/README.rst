This is an example docker with a few inputs and outputs that computes the
average color of a large image.

To build, use docker in this directory::

    docker build --force-rm -t girder/slicer_cli_web:average_color .

To run, you'll need an image that can be read by the large_image library.
You can run this as a command line, mounting a directory for input and output,
like so::

    docker run --rm -t -v /local/image/path:/input:ro -v /local/output/path:/output --rm -it girder/slicer_cli_web:average_color average_color /input/sample_image.svs /output/annotation.json --returnparameterfile /output/results.txt --channel=red

You can also enumerate available algorithms::

    docker run --rm -t girder/slicer_cli_web:average_color --list_cli

And get help for the one available algorithm::

    docker run --rm -t girder/slicer_cli_web:average_color average_color --help
