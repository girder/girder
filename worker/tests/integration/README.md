# Girder Worker Integration Tests

This directory contains scripts and files necessary to run the girder worker integration tests. Integration tests are intended to provide end-to-end validation of the girder girder-worker system. To accomplish this we use several [docker containers](https://www.docker.com/what-container) to run the necessary services; one for girder, mongodb, girder worker and rabbitmq. We then use [pytest](https://docs.pytest.org/en/latest/contents.html) to run the actual integration tests which mostly make requests against girder's API to run jobs and make assertions about their status. 


Before running the tests you will need to make sure girder-worker is installed (either in a virtual environment,  or in your system's python environment).  To run the tests first install the necessary tools:


```
cd /path/to/girder_worker/tests/integration
make
```

Then run the system:
```
make run2
# make run3 to bring up Girder/Girder Worker in Python 3 environments. 
```

and run the tests:

```
pytest -v
```

Test's may be sped up by paralleling their execution:

```
pytest -v -n 4
```

where ```4``` is the number of parallel test processes you wish to use. Please note that: _All tests should be written so that they can run in parallel_. This is critical for timely execution of the integration tests.

# Integration Test Make Targets

Girder worker's integration tests use a [Makefile](https://www.gnu.org/software/make/manual/make.html) to coordinate calls to [docker-compose](https://docs.docker.com/compose/) which orchestrates the docker containers,  and [Ansible](http://docs.ansible.com/) which manages run-time configuration of the girder/girder-worker system for use with the test suite. The targets are as follows:

+ ```initialize``` - Install the required packages to run the test infrastructure (e.g. pytest, ansible). This is also the default target (i.e. ```make``` will run this target)
+ ```run2``` - Run docker-compose to bring up the system in a Python 2 environment (that is,  Girder and Girder Worker will be run with Python 2 interpreters inside the containers),  then ansible to configure the girder/girder-worker
+ ```run3``` - Run docker-compose to bring up the system in a Python 3 environment (that is,  Girder and Girder Worker will be run with Python 3 interpreters inside the containers),  then ansible to configure the girder/girder-worker
+ ```test``` - Run the python tests locally (you may also simply run ```pytest``` from the tests/integration folder)
+ ```test2``` - Run the python tests locally excluding non-Python 3 compliant tests
+ ```clean``` - Stop all Python 2 and Python 3 containers and remove them.
+ ```nuke``` - Run ```clean``` but also remove the built images __and the girder/girder:latest{-py3} as well as girder/girder_worker:latest{-py3} images!__ (these will be recreated next time your run ```make run2``` or ```make run3```)
+ ```worker_restart2``` - Restart the worker docker container.  This is necessary if you make chances to tasks in common_tasks/
+ ```worker_restart3``` - Restart the worker docker container.  This is necessary if you make chances to tasks in common_tasks/

The following make targets use the ```docker-compose.yml``` file,  which mounts the host girder\_worker code inside the docker container.  This means you should be able to edit test endpoints and test tasks without needing to rebuild the containers. (_Note_ that you will need to restart the worker container if you change any of the test tasks in common\_tasks/). 



