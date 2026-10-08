"""Slurm job submission for apptainer tasks executed by girder-worker.

When ``GIRDER_WORKER_SLURM_SUBMIT_SCRIPT`` is set on the worker, apptainer
tasks are submitted to a slurm cluster via ``sbatch`` and monitored with
``scontrol``. When the variable is unset, apptainer tasks run directly on the
worker host without slurm.
"""
