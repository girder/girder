This Vagrantfile creates a virtualbox with a mongo sharded server with two
sharts each consisting of a three-server replica set.  This is organized as six
six docker containers for the replica sets (three for each), three docker
containers with the configuration servers, and one docker container with the
shard handler.  The main server is exposed internally on port 27017 and is
forwarded outside of the virtualbox on port 27050.

In testing, sometimes the virtualbox gets stuck provisioning.  Stop the
'vagrant up' command and retry using 'vagrant provision'.  When I tested with
the default docker version (1.0.1) rather than the newest (as currently used),
this was less of a problem, but instead I had trouble restarting the mongo
server after restarting the virtualbox.

You should be able to use this mongo server from anywhere that can reach port
27050 on the virtualbox's host machine.

When restarting the vagrant virtualbox, to restart the docker containers, ssh
in and, as root, use:
docker start rs1_srv1 rs1_srv2 rs1_srv3 rs2_srv1 rs2_srv2 rs2_srv3 cfg1 cfg2 cfg3
Wait a bit for those to start, then:
docker start mongos1

It would be nicer to do this automatically at boot, but I haven't gotten around
to it.
