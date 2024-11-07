from girder_worker import entrypoint
from girder_worker.__main__ import main
from girder_worker.entrypoint import discover_tasks

from unittest import mock
import pytest


def setup_function(func):
    if hasattr(func, 'pytestmark'):
        for m in func.pytestmark:
            if m.name == 'namespace':
                namespace = m.args[0]
                func.original = entrypoint.NAMESPACE
                entrypoint.NAMESPACE = namespace


def teardown_function(func):
    if hasattr(func, 'original'):
        entrypoint.NAMESPACE = func.original


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_get_extension_manager():
    mgr = entrypoint.get_extension_manager()
    names = sorted(mgr.names())
    assert names == ['plugin1', 'plugin2']


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_import_all_includes():
    with mock.patch('girder_worker.entrypoint.import_module') as imp:
        entrypoint.import_all_includes()
        imp.assert_has_calls(
            [mock.call('girder_worker._test_plugins.tasks')],
            any_order=True)


@pytest.mark.namespace('girder_worker._test_plugins.invalid_plugins')
def test_invalid_plugins():
    with pytest.raises(Exception):
        entrypoint.get_plugin_task_modules()


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_external_plugins():
    with mock.patch('girder_worker.app.app') as app:
        discover_tasks(app)
        app.conf.update.assert_any_call({'CELERY_INCLUDE':
                                         ['girder_worker._test_plugins.tasks']})


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_get_extensions():
    with mock.patch('girder_worker.__main__.app'):
        main()
        extensions = sorted(entrypoint.get_extensions())
        assert extensions == ['plugin1', 'plugin2']


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_get_module_tasks():
    with mock.patch('girder_worker.__main__.app'):
        main()
        extensions = sorted(entrypoint.get_module_tasks('girder_worker._test_plugins.tasks'))
        assert extensions == [
            'girder_worker._test_plugins.tasks.celery_task',
            'girder_worker._test_plugins.tasks.function_task'
        ]


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_get_extension_tasks():
    with mock.patch('girder_worker.__main__.app'):
        main()
        extensions = sorted(entrypoint.get_extension_tasks('plugin2'))
        assert extensions == [
            'girder_worker._test_plugins.tasks.celery_task',
            'girder_worker._test_plugins.tasks.function_task'
        ]


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_get_extension_tasks_celery():
    with mock.patch('girder_worker.__main__.app'):
        main()
        extensions = sorted(entrypoint.get_extension_tasks('plugin2', celery_only=True))
        assert extensions == [
            'girder_worker._test_plugins.tasks.celery_task'
        ]
