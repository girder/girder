==============
Slicer CLI Web
==============

A Girder plugin for exposing slicer execution model CLIs over the web using docker and girder_worker.

Installation
------------

Slicer CLI Web is both a Girder_ plugin and a `Girder Worker`_ plugin.  It allows dockerized tasks to be run from the Girder user interface.

Linux
=====

In linux with Python 3.6, 3.7, 3.8, 3.9, or 3.10:

Prerequisites:

- An appropriate version of Python must be installed.
- MongoDB must be installed and running.
- RabbitMQ or another broker is needed to use Girder Worker.
- Docker must be installed and the current user must be part of the docker group.

To use Girder:

.. code-block:: bash

  pip install 'girder-slicer-cli-web[girder]''
  girder serve

To use Girder Worker:

.. code-block:: bash

  pip install 'girder-slicer-cli-web[worker]'
  GW_DIRECT_PATHS=true girder_worker -l info -Ofair --prefetch-multiplier=1

The first time you start Girder, you'll need to configure it with at least one user and one assetstore (see the Girder_ documentation).  Additionally, it is recommended that you install some dockerized tasks, such as the HistomicsTK_ algorithms.  This can be done going to the Admin Console, Plugins, Slicer CLI Web settings.  Set a default task upload folder, then import the ``dsarchive/histomicstk:latest`` docker image.

Girder Plugin
-------------

Importing Docker Images
=======================

Once a docker image has been created and pushed to Docker Hub, you can register the image's CLI as a set of tasks on the server. To do so,
use the client upload script bundled with this tool. To install it, run:

.. code-block:: bash

  pip install 'girder-slicer-cli-web[client]'

Create an API key with the "Manage Slicer CLI tasks" scope, and set it in your environment and run a command like this example:

.. code-block:: bash

  GIRDER_API_KEY=my_key_vale upload-slicer-cli-task https://my-girder-host.com/api/v1 641b8578cdcf8f129805524b my-slicer-cli-image:latest

The first argument of this command is the API URL of the server, the second is a Girder folder ID where the tasks will live, and the
last argument is the docker image identifier. (If the image does not exist locally it will be pulled.) If you just want to create a
single CLI task rather than all tasks from ``--list_cli``, you can pass ``--cli=CliName``. If you wish to replace the existing tasks
with the latest specifications, also pass the ``--replace`` flag to the command.


Running CLIs
============

When you visit the item page of an imported CLI, an extra ``Configure Task`` section is shown.  You can set all of the inputs for the CLI and indicate where output files should be stored.  Selecting ``Run Task`` will have Girder Worker execute the CLI.  See the Jobs panel for progress and error messages.

Docker CLIs
-----------

Slicer CLI Web executes programs from docker images.  Any docker image can be used that complies with some basic responses from its ``ENTRYPOINT``.

Specifically, when a docker image is invoked like::

    docker run <docker image tag> --list_cli

it needs to respond with with a JSON dictionary of CLIs, where the keys of this dictionary are the names of the CLIs.  See `cli_list.json <./small-docker/cli_list.json>`_ for an example.

Each available CLI needs to report what it takes as inputs and outputs.  When the docker image is invoked like::

    docker run <docker image tag> <cli name> --xml

it needs to return an XML specification to stdout.  See `Example1.xml <./small-docker/Example1/Example1.xml>`_ for an example.

The XML must conform to the `Slicer Execution Schema <https://www.slicer.org/w/index.php?title=Documentation/Nightly/Developers/SlicerExecutionModel>`_, with a few minor additions:

- Some types (``image``, ``file``, ``transform``, ``geometry``, ``table``, ``directory``, ``item``) can have a ``reference`` property.  When ``image``, ``file``, ``item``, ``directory`` are used with Girder, if the ``reference`` property is ``_girder_id_``, then value will be passed as a Girder ID string rather than converted to a Girder resource.

- The ``region`` type can have a ``coordinateSystem`` property.

- The ``region`` type has an optional ``shapes`` property that is a comma-separated list of values that can include ``default``, ``rectangle``, ``polygon``, ``line``, ``polyline``, and ``point``, plus ``multi`` and one of ``submit`` (or ``submitoff``), ``submiton``, or ``autosubmit``.
  In the official schema, region is a vector of six values of the form x,y,z,rx,ry,rz, defining a rectangle based on its center and radius in each of three dimensions.  This is the ``default`` shape.  The ``rectangle`` shape allows a vector of four values defining a rectangle of the form x,y,width,height, where x,y is the left and top of the rectangle in pixel coordinates.  Many algorithms that accept this value accept -1,-1,-1,-1 as a default to specify the whole conceptual space.  The ``polygon`` shape allows for a list of x,y values.  Polygons must always have at least four points so that the vector of values cannot be confused with the default; repeat the first vertex at the end to specify a triangle.  The ``line`` shape allows a two-vertex line.  To disambiguate this from a rectangle, the values -2,-2 are added after the line.  The ``polyline`` shape allows a multi vertex line, indicated again by a -2,-2 value after the line.  A ``point`` is a single vertex.
  ``multi`` allow multiple shapes, indicated by separating coordinates of each shape by -1,-1.  Note that neither -1,-1 nor -2,-2 are allowed as coordinates within a shape -- to use those, specify them with decimals (e.g., -1.0,-1.0).
  The submit options will add suggestions on how the UI should handle changes.  If present, the option to auto-run a job as soon as a valid shape is set should be present.  ``autosubmit`` means this should always happen.  ``submit`` or ``submitoff`` offers this as a setting but is default to not submit the job.  ``submiton`` offers this as a setting and defaults to submitting the job.

- Some input types (``image``, ``file``, ``item``, ``directory``) can have ``defaultNameMatch``, ``defaultPathMatch``, and ``defaultRelativePath`` properties.  The first two are regular expressions designed to give a UI a value to match to prepopulate default values from files or paths that match the regex.  ``defaultNameMatch`` is intended to match the final path element, whereas ``defaultPathMatch`` is used on the entire path as a combined string.  ``defaultRelativePath`` is used to find a value that has a path relative to some base.  In the Girder UI, this might be from an item.

- Input types can have a ``datalist`` property.  If this is present, when the CLI is first loaded or, possibly periodically after parameters have been changed, the CLI may be called with optional parameters.  The CLI is expected to return a new-line separated list of values that can be used as recommended inputs.  As an example, a ``string`` input might have a ``datalist`` of ``--enumerate-options``; the cli would be called with the existing parameters PLUS the extra parameter specified by ``datalist``.  If the result is sensible, the input control would expose this list to the user.  The ``datalist`` property is a json-encoded dictionary that overrides other parameters.  This should override parameters that aren't needed to be resolved to produce the datalist (e.g., input and output files) as that will speed up the call.  The CLI should respond to the modified call with a response that contains multiple ``<element>some text</element>`` values that will be the suggested data for the control.

- There are some special string parameters that, if unspecified or blank, are autopopulated.  String parameters with the names of ``girderApiUrl`` and ``girderToken`` are populated with the appropriate url and token so that a running job could use girder_client to communicate with Girder.

- Internally, the ``ctk_cli`` module is used.  This has two differences from the Slicer Execution Schema that are technically bugs.

  - Enumerations have bare elements under the appropriate parent tag.  That is, instead of a structure like ``<string-enumeration>...<enumeration><element>Value 1</element><element>Value 2</element>...</enumeration></string-enumeration>``, the ``<enumeration>`` tag is omitted: ``<string-enumeration>...<element>Value 1</element><element>Value 2</element>...</string-enumeration>``.

  - Booleans specify a true or false value after the flag or long flag.  The Slicer Execution Schema states that booleans should be false by default and the presence of the flag should make them true.  The ``ctk_cli`` specifies that they take a single ``true`` or ``false`` parameter.  This doesn't change the xml; it changes what is passed to the CLI.  Instead of passing ``--longflag`` to set the flag to true, ``--longflag true`` must be passed.

Docker CLIs with GPU support
----------------------------

When girder_worker runs docker images, the containers are started with gpu support only if the docker image has a label saying it should use an nvidia driver (add ``LABEL com.nvidia.volumes.needed=nvidia_driver`` to the Dockerfile).

--list_cli response format
==========================

The response from a docker image invoked with the ``--list_cli`` option needs to be a JSON response returning a single object.  The object must contain a key for each CLI.  Each key has a value used to parse or handle the CLI.

Here is a commented example::

    {
      // the key is the name of the CLI
      "Example1": {
        // type is typically either "python" or "cxx".  The default program
        // either runs "python <CLI key>/<CLI key>.py" for python or
        // "<CLI key>/<CLI key>" for cxx.
        "type": "python"
      },
      "Example2": {
        "type": "python",
        // The desc-type defaults to xml but can be any of "xml", "json", or
        // "yaml".  To get the CLI command line options, the CLI is invoked via
        //   docker run <docker image tag> <cli name> --<desc-type>
        "desc-type": "json"
      },
      "AnotherName": {
        // The alias allows the CLI to be invoked as either the key or the
        // alias.  This runs Example2 when invoked as AnotherName.
        "alias": "Example2",
        "type": "python"
      },
      "Example3": {
        "type": "python",
        // docker-params is a dictionary of parameters passed to the docker API
        // when the docker container is created and run.  Not all possible tags
        // are passed through.  See the docker python module for options:
        // https://docker-py.readthedocs.io/en/stable/containers.html
        "docker-params": {
          "ipc_mode": "host"
        }
      }
    }

CLI Endpoints
=============

Each exposed CLI is added as an endpoint using the REST path of ``slicer_cli_web/<docker image tag and version>/<cli command>/run`` and also using the REST path of ``slicer_cli_web/<internal item id>/run``, where ``<docker image tag and version>`` is the combined tag and version with slashes, colons, and at signs replaced by underscores.  All command line parameters can be passed as endpoint query parameters.  Input items, folders, and files are specified by their Girder ID.  Input images are specified by a Girder file ID.  Output files are specified by name and with an associated parameter with the same name plus a ``_folder`` suffix with a Girder folder ID.

Small Example CLI Docker
========================

The small example CLI docker image can be built locally via ``docker build --force-rm -t girder/slicer_cli_web:small .``, or pulled from Docker Hub.

Batch Processing
----------------

All CLIs that take any single item, image, or files as inputs can be run on a set of such resources from a single directory.  For non-batch processing, the
ID of the image, item, or file is passed to ``<param>``.  For batch processing, the ID of a folder is passed to ``<param>_folder`` and a regular expression is passed to <param>.  All items in that folder whose name matches the regex are processed.  For images, only items that contain large_images are considered.  For files, the first file in each considered item is used.

If two inputs have batch specifications, there must be a one-to-one correspondence between the each of the lists of items determined by the folder ID and regular expression.  All of the lists are enumerated sorted by the lower case item name.

When running a batch job, a parent job initiates ordinary (non-batch) jobs.  The parent job will only start another child job when the most recent child job is no longer waiting to start.  This allows non-batch jobs or multiple batch jobs' children to naturally interleave.  The parent job can be canceled which will stop it from scheduling any more child jobs.

Templated Inputs
----------------

Any CLI parameter that takes a value that isn't a Girder resource identifier can be specified with a Jinja2-style template string.

For instance, instead of typing an explicit output file name, one can specify something like ``{{title}}-{{reference_base}}-{{now}}{{extension}}``.  If this were being run on a task called "Radial Blur" on an image called "SampleImage.tiff", where the output image referenced the image image and had a list of file extensions starting with ".png", this would end up being converted to the value ``Radial Blur-SampleImage-20210428-084321.png``.

The following template values are handled identically for all parameters:

- ``{{title}}``: the displayed CLI task title.
- ``{{task}}``: the internal task name (this usually doesn't have spaces in it)
- ``{{image}}``: the tag of the Docker image used for the task
- ``{{now}}``: the local time the job started in the form yyyymmdd-HHMMSS.  You can use ``yyyy``, ``mm``, ``dd``, ``HH``, ``MM``, ``SS`` for the four digit year, and two digit month, day, 24-hour, minute, and second.
- ``{{parameter_<name of cli parameter>}}``: any parameter that isn't templated can be referenced by its name.  For instance, in Example1 in the small-docker cli in this repo, ``{{parameter_stringChoice}}`` would get replaced by the value passed to the stringChoice parameter.
- ``{{parameter_<name of cli parameter>_base}}`` is the same as the previous item except that if the right-most part of the parameter looks like a file extension, it is removed.  This can be used to get the base name of file parameters.

The following template parameters are only handled on the web client:
- ``{#control:<selector>#}``: If specified for the value of a parameter, use the value of the selected field from the DOM.  For instance, ``{#control:.h-zoom-value#}`` could get the current image zoom level.

There are also template values specific to individual parameters:

- ``{{name}}``: the name of this parameter.  This usually doesn't have any spaces in it.
- ``{{label}}``: the label of the is parameter.  This is what is displayed in the user interface.
- ``{{description}}``: the description of the parameter.
- ``{{index}}``: the index, if any, of the parameter.
- ``{{default}}``: the default value, if any, of the parameter.
- ``{{extension}}``: the first entry in the ``fileExtension`` value of the parameter, if any.
- ``{{reference}}``: if the parameter has a reference to another parameter, this returns that parameter's value.  It is equivalent to ``{{parameter_<reference>}}``.
- ``{{reference_base}}``: the reference value mentioned previously striped of the right-most file extension.

If the local (server) environment has any environment variables that begin with ``SLICER_CLI_WEB_``, these are accessible in the templates as ``{{env_(name)}}``.  For instance, ``SLICER_CLI_WEB_DASK_SERVER`` would be accessible as ``{{env_DASK_SERVER}}``.

.. _Girder: http://girder.readthedocs.io/en/latest/
.. _Girder Worker: https://girder-worker.readthedocs.io/en/latest/
.. _HistomicsTK: https://github.com/DigitalSlideArchive/HistomicsTK
