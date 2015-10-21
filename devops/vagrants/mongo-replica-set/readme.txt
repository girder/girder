This Vagrantfile creates a virtualbox with a mongo replica set spread across
three docker containers.  They are exposed on ports 27060, 27061, 27062 and
have a replica set name of 'rs1'.

At least under my test environment, another virtualbox can access these by
using a mongo uri of
mongodb://10.0.2.2:27060,10.0.2.2:27061,10.0.2.2:27062/?replicaSet=rs1

Because the replica set expects to talk to its peers via 10.0.2.2:(port), this
may not work in another networking enviroment.

When restarting the vagrant virtualbox, to restart the docker containers, ssh
in and, as root, use:
docker start rs1_srv1 rs1_srv2 rs1_srv3
