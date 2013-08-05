# System Prerequisites

The following software packages are required to be installed on your system:

* [python](http://python.org/)
* [pip](https://pypi.python.org/pypi/pip)
* [MongoDB](http://www.mongodb.org/)
* [node.js](http://nodejs.org/)

See the specific instructions for your platform below.

* [Ubuntu](#ubuntu)
* [Red Hat](#rhel--fedora--centos)
* [Mac OSX](#mac-osx)

## Ubuntu

Use APT to install the prerequisites on Ubuntu.

    sudo apt-get install mongodb python-pip

Node.js currently isn't in the standard repositories, so run:

    sudo apt-get install python-software-properties python g++ make
    sudo add-apt-repository ppa:chris-lea/node.js
    sudo apt-get update
    sudo apt-get install nodejs

## RHEL / Fedora / CentOS

TODO

## Mac OSX

It is recommened to use [Homebrew](http://brew.sh/) to install the required packages on OSX.

To install all of the prerequisites at once just use:

    brew install python mongodb node

> __Note:__ OSX ships with python in /usr/bin, so you might need to change your PATH or
> explicitly run /usr/local/bin/python when invoking the server so that you use the version
> with the correct site packages installed.
