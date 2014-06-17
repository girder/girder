#!/bin/bash
/usr/bin/screen -d -m /bin/bash -c '/usr/bin/python -m girder 2>&1 | tee /home/vagrant/girder_output.log'
