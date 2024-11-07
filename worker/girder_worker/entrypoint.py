from importlib import import_module
import celery
from girder_worker.utils import decorators

from stevedore import extension


#: Defines the namespace used for plugin entrypoints
NAMESPACE = 'girder_worker_plugins'


def _handle_entrypoint_errors(mgr, entrypoint, exc):
    raise exc


def get_extension_manager(app=None):
    """Get an extension manager for the plugin namespace."""
    if app is None:
        app = celery.current_app

    return extension.ExtensionManager(
        namespace=NAMESPACE,
        invoke_on_load=True,
        invoke_args=(app,),
        on_load_failure_callback=_handle_entrypoint_errors
    )


def get_plugin_task_modules(app=None):
    """Return task modules defined by plugins."""
    includes = []
    for ext in get_extension_manager(app=app):
        includes.extend(ext.obj.task_imports())
    return includes


def import_all_includes():
    """Import all task modules for their side-effects."""
    for module in get_plugin_task_modules():
        import_module(module)


def get_extensions(app=None):
    """Get a list of installed extensions."""
    return [ext.name for ext in get_extension_manager(app)]


def get_module_tasks(module_name):
    """Get all tasks defined in a python module.

    :param str module_name: The importable module name
    """
    module = import_module(module_name)
    tasks = {}

    if module is None:
        return tasks

    for name, func in vars(module).items():
        full_name = '%s.%s' % (module_name, name)
        if not callable(func):
            # filter out objects that are not callable
            continue

        try:
            decorators.get_description_attribute(func)
            tasks[full_name] = func
        except decorators.MissingDescriptionException:
            pass
    return tasks


def get_extension_tasks(extension, app=None, celery_only=False):
    """Get the tasks defined by a girder_worker extension.

    :param str extension: The extension name
    :param app: The celery app instance
    :param bool celery_only: If true, only return celery tasks
    """
    manager = get_extension_manager(app)
    imports = manager[extension].obj.task_imports()
    tasks = {}
    for module_name in imports:
        tasks.update(get_module_tasks(module_name))

    if celery_only:  # filter celery tasks
        if app is None:
            from .app import app
        tasks = {
            key: tasks[key] for key in tasks if key in app.tasks
        }

    return tasks


def discover_tasks(app):
    app.conf.update({
        'CELERY_INCLUDE': get_plugin_task_modules()
    })
