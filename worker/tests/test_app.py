import celery

from girder_worker.task import (
    GirderAsyncResult,
    Task
)
from girder_worker.utils import (
    BUILTIN_CELERY_TASKS,
    _maybe_model_repr
)
from unittest import mock
import pytest


RESERVED_HEADERS = [
    ('girder_client_token', 'GIRDER_CLIENT_TOKEN'),
    ('girder_api_url', 'GIRDER_API_URL'),
    ('girder_result_hooks', 'GIRDER_RESULT_HOOKS'),
    ('girder_client_session_kwargs', 'GIRDER_CLIENT_SESSION_KWARGS')
]

RESERVED_OPTIONS = [
    ('girder_user', 'GIRDER_USER'),
    ('girder_job_title', 'GIRDER_JOB_TITLE'),
    ('girder_job_type', 'GIRDER_JOB_TYPE'),
    ('girder_job_public', 'GIRDER_JOB_PUBLIC'),
    ('girder_job_handler', 'GIRDER_JOB_HANDLER'),
    ('girder_job_other_fields', 'GIRDER_JOB_OTHER_FIELDS')
]


# This function returns a Task() object and tweaks the task's
# request_stack to include a Context object. args and kwargs are
# passed directly to the generated Context object. See:
# celery.app.task.Context for more info.
def _task_with_request(*args, **kwargs):
    task = Task()
    task.name = 'example.task'
    task.request_stack = celery.utils.threads.LocalStack()
    task.push_request(*args, **kwargs)
    return task


class MockTrans:
    def __init__(self, arg):
        self.arg = arg

    def transform(self, *args, **kwargs):
        return self.arg


class MockNonTrans:
    pass


MockNonTransObj = MockNonTrans()


# Note: This test checks whether the
# girder_worker.app.Task.reserved_headers are the same as the headers
# defined in RESERVED_HEADERS. If it is failing it is probably because
# you added a reserved header to girder_worker.app.Task and not to
# RESERVED_HEADERS
def test_TASK_reserved_headers_same_as_test_reserved_headers():
    assert set(Task.reserved_headers) == {h for h, _ in RESERVED_HEADERS}


# Note: This test checks whether the
# girder_worker.app.Task.reserved_options are the same as the options
# defined in RESERVED_OPTIONS. If it is failing it is probably because
# you added a reserved options to girder_worker.app.Task and not to
# RESERVED_OPTIONS
def test_TASK_reserved_options_same_as_test_reserved_options():
    assert set(Task.reserved_options) == {h for h, _ in RESERVED_OPTIONS}


def test_GirderAsyncResult_job_property_returns_None_on_ImportError():
    gar = GirderAsyncResult('BOGUS_TASK_ID')
    assert gar.job is None


def test_GirderAsyncResult_job_property_calls_findOne_on_girder_job_model():
    gar = GirderAsyncResult('BOGUS_TASK_ID')

    with mock.patch('cherrypy.request.app', return_value=True):
        with mock.patch.dict('sys.modules',
                             **{'girder.plugins': mock.MagicMock(),
                                'girder.plugins.worker': mock.MagicMock(),
                                'girder.plugins.worker.utils': mock.MagicMock()}):
            with mock.patch('girder.utility.model_importer.ModelImporter') as mi:
                gar.job
                mi.model.return_value.findOne.assert_called_once_with({
                    'celeryTaskId': 'BOGUS_TASK_ID'
                })


def test_GirderAsyncResult_job_property_returns_None_if_no_jobs_found():
    gar = GirderAsyncResult('BOGUS_TASK_ID')
    with mock.patch('girder.utility.model_importer.ModelImporter') as mi:
        mi.model.return_value.findOne.side_effect = IndexError()
        assert gar.job is None


def test_Task_AsynResult_of_type_GirderAsyncResult():
    assert isinstance(Task().AsyncResult('BOGUS_TASK_ID'), GirderAsyncResult)


@pytest.mark.parametrize('name', BUILTIN_CELERY_TASKS)
def test_Task_apply_async_does_not_meddle_with_headers_on_builtin_tasks(name):
    kwargs = dict(RESERVED_OPTIONS)

    with mock.patch('girder_worker.task.celery.Task.apply_async', spec=True) as mock_apply_async:
        t = Task()
        t.name = name
        t.apply_async((), kwargs, **{})
        mock_apply_async.assert_called_once()

    # Expected behavior is that reserved options will be popped out of kwargs
    # This tests to make sure that we never meddle with headers on builtin tasks
    for k, _ in RESERVED_OPTIONS:
        assert k in kwargs


@pytest.mark.parametrize('header,expected', RESERVED_HEADERS)
def test_Task_apply_async_reserved_headers_in_options(header, expected):
    with mock.patch('girder_worker.task.celery.Task.apply_async', spec=True) as mock_apply_async:
        t = Task()
        t.name = 'example.task'
        t.apply_async((), {}, **{header: expected})
        margs, mkwargs = mock_apply_async.call_args
        assert 'headers' in mkwargs
        assert header in mkwargs['headers']
        assert mkwargs['headers'][header] == expected


@pytest.mark.parametrize('header,expected', RESERVED_HEADERS)
def test_Task_apply_async_reserved_headers_in_kwargs(header, expected):
    with mock.patch('girder_worker.task.celery.Task.apply_async', spec=True) as mock_apply_async:
        t = Task()
        t.name = 'example.task'
        t.apply_async((), {header: expected})
        margs, mkwargs = mock_apply_async.call_args
        assert 'headers' in mkwargs
        assert header in mkwargs['headers']
        assert mkwargs['headers'][header] == expected


@pytest.mark.parametrize('header,expected', RESERVED_HEADERS)
def test_Task_delay_reserved_headers_in_kwargs(header, expected):
    with mock.patch('girder_worker.task.celery.Task.apply_async', spec=True) as mock_apply_async:
        t = Task()
        t.name = 'example.task'
        t.delay(**{header: expected})
        margs, mkwargs = mock_apply_async.call_args
        assert 'headers' in mkwargs
        assert header in mkwargs['headers']
        assert mkwargs['headers'][header] == expected


@pytest.mark.parametrize('option,expected', RESERVED_OPTIONS)
def test_Task_apply_async_reserved_options_in_options(option, expected):
    with mock.patch('girder_worker.task.celery.Task.apply_async', spec=True) as mock_apply_async:
        t = Task()
        t.name = 'example.task'
        t.apply_async((), **{option: expected})
        margs, mkwargs = mock_apply_async.call_args
        assert 'headers' in mkwargs
        assert option in mkwargs['headers']
        assert mkwargs['headers'][option] == expected


@pytest.mark.parametrize('option,expected', RESERVED_OPTIONS)
def test_Task_apply_async_reserved_options_in_kwargs(option, expected):
    with mock.patch('girder_worker.task.celery.Task.apply_async', spec=True) as mock_apply_async:
        t = Task()
        t.name = 'example.task'
        t.apply_async((), {option: expected})
        margs, mkwargs = mock_apply_async.call_args
        assert 'headers' in mkwargs
        assert option in mkwargs['headers']
        assert mkwargs['headers'][option] == expected


@pytest.mark.parametrize('option,expected', RESERVED_OPTIONS)
def test_Task_delay_reserved_options_in_kwargs(option, expected):
    with mock.patch('girder_worker.task.celery.Task.apply_async', spec=True) as mock_apply_async:
        t = Task()
        t.name = 'example.task'
        t.delay(**{option: expected})
        margs, mkwargs = mock_apply_async.call_args
        assert 'headers' in mkwargs
        assert option in mkwargs['headers']
        assert mkwargs['headers'][option] == expected


@pytest.mark.parametrize('header,expected', RESERVED_HEADERS + RESERVED_OPTIONS)
def test_Task_apply_async_reserved_in_options_with_existing_header_option(header, expected):
    with mock.patch('girder_worker.task.celery.Task.apply_async', spec=True) as mock_apply_async:
        t = Task()
        t.name = 'example.task'
        t.apply_async((), {}, **{header: expected, 'headers': {'some': 'header'}})
        margs, mkwargs = mock_apply_async.call_args
        assert 'headers' in mkwargs
        assert header in mkwargs['headers']
        assert mkwargs['headers'][header] == expected


# TODO: it would be nice to check that an empty set of arguments calls
# with an empty set of arguments, (i.e.  ```((), ())``` )
# unfortunately this ends up throwing TypeError("'self' parameter
# lacking default value",) which from some cursory googling looks like
# an internal Mock thing having to do with wrapped functions.
@pytest.mark.parametrize('arguments,transformed', [
    ((1,), (1,)),  # noqa E202
    ((1.0,), (1.0,)),  # noqa E202
    (('string',), ('string',)),  # noqa E202
    ((b'bytes',), (b'bytes',)),  # noqa E202
    ((('tuple',),), (('tuple',),)),  # noqa E202
    ((['list', 'of', 'items'],), (['list', 'of', 'items'],)),  # noqa E202
    (({'key': 'value'},), ({'key': 'value'},)),  # noqa E202
    ((MockNonTrans, ), (MockNonTrans,)),  # noqa E202
    ((MockNonTransObj, ), (MockNonTransObj,)),  # noqa E202
    (('multiple', 'arguments'), ('multiple', 'arguments')),  # noqa E202
    ((MockTrans('TEST'),), ('TEST',)),  # noqa E202
    ((MockTrans('TEST1'), MockTrans('TEST2')), ('TEST1', 'TEST2')),  # noqa E202
    (('TEST1', MockTrans('TEST2')), ('TEST1', 'TEST2')),  # noqa E202
    (([MockTrans('TEST1'), MockTrans('TEST2')],), (['TEST1', 'TEST2'],)),  # noqa E202
    (((MockTrans('TEST1'), MockTrans('TEST2')),), (('TEST1', 'TEST2'),)),  # noqa E202
    (({'key': MockTrans('TEST')},), ({'key': 'TEST'},)),  # noqa E202
    (({'outer': {'inner': MockTrans('TEST')}},), ({'outer': {'inner': 'TEST'}},)),  # noqa E202
    ((MockNonTransObj,
      {'outer': {'inner': MockTrans('TEST'),
                 'other': MockNonTransObj}},
      (MockTrans('TEST1'), MockNonTransObj, MockTrans('TEST2'))),
     (MockNonTransObj,
      {'outer': {'inner': 'TEST',
                 'other': MockNonTransObj}},
      ('TEST1', MockNonTransObj, 'TEST2')))

], ids=[
    'Single Int',
    'Single Float',
    'Single String',
    'Single Bytes',
    'Single Tuple',
    'Single List',
    'Single Dict',
    'Single NonTrans Class',
    'Single NonTrans Object',
    'Multiple NonTrans Arguments',
    'Single Trans',
    'Multiple Trans Arguments',
    'Mixed Trans and NonTrans Args',
    'Single List of Trans Arguments',
    'Single Tuple of Trans Arguments',
    'Single Dict of Trans Arguments',
    'Nested Dict of Trans Arguments',
    'Complex'
])
def test_Task___call___transforms_or_passes_through_arguments(arguments, transformed):
    with mock.patch('girder_worker.task.celery.Task.__call__', spec=True) as mock_call:
        task = _task_with_request()
        task(*arguments)
        mock_call.assert_called_once_with(*transformed)


# Note: We have to add 'FIXME' as an argument to task(...) and
# mock_call to avoid the same TypeError as observed in the prevous
# test.
@pytest.mark.parametrize('kwargs,transformed', [
    ({'k': 1}, {'k': 1}),  # noqa E202
    ({'k': 1.0}, {'k': 1.0}),  # noqa E202
    ({'k': 'string'}, {'k': 'string'}),  # noqa E202
    ({'k': b'bytes'}, {'k': b'bytes'}),  # noqa E202
    ({'k': ('some', 'tuple')}, {'k': ('some', 'tuple')}),  # noqa E202
    ({'k': ['some', 'list']}, {'k': ['some', 'list']}),  # noqa E202
    ({'outer': {'inner': 'value'}}, {'outer': {'inner': 'value'}}),  # noqa E202
    ({'k1': 'v1', 'k2': 'v2'}, {'k1': 'v1', 'k2': 'v2'}),  # noqa E202
    ({'k': MockNonTransObj}, {'k': MockNonTransObj}),  # noqa E202
    ({'k': MockNonTrans}, {'k': MockNonTrans}),  # noqa E202
    ({'k': MockTrans('TEST')}, {'k': 'TEST'}),  # noqa E202
    ({'k': (MockTrans('TEST1'), MockTrans('TEST2'))}, {'k': ('TEST1', 'TEST2')}),  # noqa E202
    ({'k': [MockTrans('TEST1'), MockTrans('TEST2')]}, {'k': ['TEST1', 'TEST2']}),  # noqa E202
    ({'outer': {'inner': MockTrans('TEST')}}, {'outer': {'inner': 'TEST'}}),  # noqa E202
    ({'k': MockTrans('TEST'), 'k2': 'v2'}, {'k': 'TEST', 'k2': 'v2'}),  # noqa E202
    ({'k ': MockNonTransObj,
      'k2': MockTrans('TEST'),
      'k3': {'k ': MockTrans('TEST'),
             'k2': MockNonTransObj},
      'k4': (MockTrans('TEST1'), MockNonTransObj, MockTrans('TEST2'))},
     {'k ': MockNonTransObj,
      'k2': 'TEST',
      'k3': {'k ': 'TEST',
             'k2': MockNonTransObj},
      'k4': ('TEST1', MockNonTransObj, 'TEST2')}),
], ids=[
    'Dict w/Int',
    'Dict w/Float',
    'Dict w/String',
    'Dict w/Bytes',
    'Dict w/Tuple',
    'Dict w/List',
    'Nestd Dict',
    'Dict with multiple Keys',
    'Dict w/NonTrans Obj',
    'Dict w/NonTrans Class',
    'Dict w/Trans Obj',
    'Dict w/Tuple of Trans Objs',
    'Dict w/List of Trans Objs',
    'Nested Dict w/Trans Obj',
    'MultiKey Dict w/Trans Obj',
    'Complex'
])
def test_Task___call___transforms_or_passes_through_kwargs(kwargs, transformed):
    with mock.patch('girder_worker.task.celery.Task.__call__', spec=True) as mock_call:
        task = _task_with_request()
        task('FIXME', **kwargs)
        mock_call.assert_called_once_with('FIXME', **transformed)


class MockResultTrans:
    def __init__(self, func):
        self.func = func

    def transform(self, *args, **kwargs):
        return self.func(*args, **kwargs)


@pytest.mark.parametrize('results,hooks,transformed', [
    (1, (MockResultTrans(lambda x: x + 1),), 2),      # noqa E202
    ((1, 2), (MockResultTrans(lambda x: x + 1),
               MockResultTrans(lambda x: x + 1)), (2, 3)),  # noqa E202
    ((1, 2), (MockResultTrans(lambda x: x + 1), None), (2, 2)),  # noqa E202
    ((1, 2), (None, MockResultTrans(lambda x: x + 1)), (1, 3)),  # noqa E202
    ((1, 2), (MockResultTrans(lambda x: x + 1), ), (2, 2)),  # noqa E202
], ids=[
    'Single Return Value',
    'Tuple Return Value',
    'Tuple, Second Trans None',
    'Tuple, First Trans None',
    'Tuple, Missing Tail Trans'
])
def test_Task___call___transforms_or_passes_through_girder_result_hooks(
        results, hooks, transformed):
    with mock.patch('girder_worker.task.celery.Task.__call__',
                    return_value=results):
        task = _task_with_request(girder_result_hooks=hooks)
        assert task('ARG1', kwarg='KWARG1') == transformed


class MockModelRepr:
    def __init__(self, arg):
        self.arg = arg

    def _repr_model_(self):
        return repr(self.arg)


@pytest.mark.parametrize('obj,expected', [
    ('string', 'string'),
    (b'bytes', B'bytes'),
    (1, 1),
    (1.0, 1.0),
    ({'key': 'value'}, {'key': 'value'}),
    (['some', 'list'], ['some', 'list']),
    (('tuple',), ('tuple', )),
    (MockModelRepr('TEST'), '\'TEST\'')
])
def test__maybe_model_repr(obj, expected):
    assert _maybe_model_repr(obj) == expected
