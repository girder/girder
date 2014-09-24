Build the Sphinx Documentation
==============================

In order to build the `Sphinx <http://sphinx-doc.org>`_ documentation, you can
use the Grunt task at the top level like so: ::

    grunt docs

or manually run the Makefile here: ::

    make html

This assumes that the Sphinx package is installed in your site packages or
virtual environment. If that is not yet installed, it can be done using
**pip**. ::

    pip install sphinx
