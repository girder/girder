"""Apptainer (singularity) support package for slicer_cli_web.

The ``slicer_cli_web_singularity`` entry point in the
``girder_worker_plugins`` namespace (declared in girder-slicer-cli-web's own
package metadata) loads this plugin unconditionally, but the plugin returns no
task modules unless the ``GIRDER_WORKER_SINGULARITY_ENABLED`` environment
variable is set on the worker. The server side is gated by the
``slicer_cli_web.singularity_enabled`` girder setting (seedable via the
``GIRDER_SETTING_SLICER_CLI_WEB_SINGULARITY_ENABLED`` environment variable).
"""
