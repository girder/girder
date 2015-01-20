Python Client and Girder CLI
============================

In addition to the web clients, Girder comes with a python client library and
a CLI to allow for programmatic interaction with a Girder server, and also to
workaround limitations of the web client. For example, the python CLI makes it
much easier to upload a large, nested hierarchy of data from a local directory
to Girder, and also makes it much easier to download a large, nested hierarchy
of data from Girder to a local directory.

The Command Line Interface
--------------------------

<<< Mike please document >>>


The Python Client Library
-------------------------

For those wishing to write their own python scripts that interact with Girder, we
recommend using the Girder python client library, documented below.

.. automodule:: girder_client
    :members:
