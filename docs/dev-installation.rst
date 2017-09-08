
Developer Installation 
====================== 
 
You can either install Girder natively on you machine or inside a virtual
machine with Vagrant. 
 
Virtual Machine 
+++++++++++++++ 
 
The easiest way to develop for girder is within a virtual machine using Vagrant.
For this, you need `Vagrant <https://www.vagrantup.com/downloads.html`_ and `VirtualBox <https://www.virtualbox.org/wiki/Downloads>`_. 
Girder is tested to work seamlessly with Vagrant 2.0 and VirtualBox 5.1. 
 
Once you have those installed, obtain the Girder source code by cloning the Git 
repository on `GitHub <https://github.com>`_: :: 
 
    git clone https://github.com/girder/girder.git 
    cd girder 
 
Inside of the Girder directory, simply run: :: 
     
    vagrant up 
 
This creates a Virtual Ubuntu 14.04 machine with all the necessary requirements. 
After it completes, Girder will be up and running at http://localhost:9080/ 
 
The VM is linked to your local Girder directory, so changes made locally will 
impact the Girder instance running in the VM.  
 
To access the VM, inside of the Girder directory, run: :: 
 
    vagrant ssh 
 
This takes you inside of VM. 
 
 
Native Installation 
+++++++++++++++++++  
 
Before you install, see the :doc:`prerequisites` guide to make sure you 
have all required system packages installed. 
 
Obtain the Girder source code by cloning the Git repository on 
`GitHub <https://github.com>`_: :: 
 
    git clone https://github.com/girder/girder.git 
    cd girder 
 
To run the server, you must install some external Python package 
dependencies: :: 
 
    pip install -e . 
 
or: :: 
 
    pip install -e .[plugins] 
 
to install the plugins as well. 
 
.. note:: This will install the most recent versions of all dependencies. 
   You can also try to run ``pip install -r requirements.txt`` to duplicate 
   the exact versions used by our CI testing environment; however, this 
   can lead to problems if you are installing other libraries in the same 
   virtual or system environment. 
 
To build the client-side code project, cd into the root of the repository 
and run: :: 
 
    girder-install web 
 
This will run multiple `Grunt <http://gruntjs.com>`_ tasks, to build all of 
the Javascript and CSS files needed to run the web client application. 
 
