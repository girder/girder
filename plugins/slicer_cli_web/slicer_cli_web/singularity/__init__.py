"""Singularity support package for slicer_cli_web."""

import functools
from importlib import metadata


@functools.lru_cache(maxsize=1)
def singularity_extension_installed():
    """
    Return True only when the optional slicer_cli_web singularity worker plugin
    has been installed and registered via entry points.
    """
    try:
        entry_points = metadata.entry_points()
        if hasattr(entry_points, 'select'):
            return bool(entry_points.select(
                group='girder_worker_plugins',
                name='slicer_cli_web_singularity',
            ))
        return any(
            ep.group == 'girder_worker_plugins' and ep.name == 'slicer_cli_web_singularity'
            for ep in entry_points
        )
    except Exception:
        return False
