Worker Management
-----------------

The slicer_cli_web plugin has a simple worker management capability.  This uses a configuration file that lists workers than can be started and stopped via shell commands.  If more jobs are in the queue than started workers, then additional workers will be started.  When ALL jobs have been stopped for some duration, all workers are stopped.

The config file is a yaml file stored anywhere in the system.  The specific item holding the file can be configured in the plugin's settings.

An example file illustrates the options::

    ---
    idle-time:
      # This is the duration in seconds that will elapse from when all jobs are
      # finished to when the workers will be stopped.  The default is 300
      # seconds.
      all: 300
    workers:
      # This is a list of workers
      -
        # name is optional
        name: 'Example Worker'
        # start is required.  It is a shell command that is run as the same
        # user as started girder
        start: start_worker.sh
        # stop is required.  It is a shell command that is run as the same
        # user as started girder
        stop: stop_worker.sh
        # concurrency is the number of jobs that the worker can handle.  It is
        # optional, but must be a positive integer.  The default is 1.
        concurrency: 2
    # If initial-stop is not False, then all workers are stopped when the main
    # application is first started.  This ensure workers are not abandoned, but
    # may prevent workers from finishing during a benign server restart.
    initial-stop: True

This could be used, for instance, to start and stop EC2 instances with the appropriate commands.
