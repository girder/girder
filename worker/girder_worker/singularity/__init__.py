"""Apptainer (singularity) execution support for girder-worker.

Tasks are only registered when the ``GIRDER_WORKER_SINGULARITY_ENABLED``
environment variable is set on the worker process; the ``singularity`` entry
point in the ``girder_worker_plugins`` namespace (declared in girder-worker's
own package metadata) loads this plugin unconditionally, but
``SingularityPlugin.task_imports`` returns no task modules without the flag, so
an installation without it behaves exactly like stock girder-worker.
"""
