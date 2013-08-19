Girder
======

Data Management Toolkit (working title)

## Install

Before you install, see the [Installing system prerequisites](docs/manual/system_install.md)
guide to make sure you have all required system packages installed.

To run the server, you must install the following python packages:

    pip install pymongo cherrypy bcrypt

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

To run the server, first make sure the mongo daemon is running. To manually start it, run:

    mongod &

Then, just run:

    python -m girder
    
Then open http://localhost:8080/ in your web browser, and you should see the application.


