Build the Sphinx Documentation
==============================

In order to build the sphinx documentation, you can use the grunt task
at the top level like so: ::

    grunt docs

or manually run the makefile here: ::

    make html

This assumes that the sphinx package is installed in your site packages or
virtual environment. If that is not yet installed, it can be done using pip. ::

    pip install sphinx
