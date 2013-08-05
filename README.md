dmtk
====

Data Management Toolkit
(working title)

## Install

Before you install, see the [Installing system prerequisites](docs/manual/prereqs.md)
guide to make sure you have all required system packages installed.

To run the server, you must install the [PyMongo](http://api.mongodb.org/python/current/)
and [CherryPy](http://www.cherrypy.org) python packages:

    pip install pymongo cherrypy

Before you can build the client-side code project, you must install the [Grunt](http://gruntjs.com)
command line utilities:

    npm install -g grunt grunt-cli

Then cd into the root of the repository and run:

    npm install

Finally, when all node packages are installed, run:

    grunt init

## Build

To build the client side code, run the following command from within the repository:

    grunt

Run this command any time you change a JavaScript or CSS file under __clients/web__.

## Run

To run the server, just invoke the following script:

    python server/main.py


