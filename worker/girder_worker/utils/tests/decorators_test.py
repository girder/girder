import pytest

from girder_worker_utils import decorators
from girder_worker_utils import types
from girder_worker_utils.decorators import argument


@argument('n', types.Integer, help='The element to return')
def fibonacci(n):
    """Compute a fibonacci number."""
    if n <= 2:
        return 1
    return fibonacci(n - 1) + fibonacci(n - 2)


@argument('val', types.String, help='The value to return')
def keyword_func(val='test'):
    """Return a value."""
    return val


@argument('arg1', types.String)
@argument('arg2', types.StringChoice, choices=('a', 'b'))
@argument('kwarg1', types.StringVector)
@argument('kwarg2', types.Number, min=0, max=10)
@argument('kwarg3', types.NumberMultichoice, choices=(1, 2, 3, 4, 5))
def complex_func(arg1, arg2, kwarg1=('one',), kwarg2=4, kwarg3=(1, 2)):
    return {
        'arg1': arg1,
        'arg2': arg2,
        'kwarg1': kwarg1,
        'kwarg2': kwarg2,
        'kwarg3': kwarg3
    }


@argument('item', types.GirderItem)
@argument('folder', types.GirderFolder)
def girder_types_func(item, folder):
    return item, folder


def test_positional_argument():
    desc = fibonacci.describe()
    assert len(desc['inputs']) == 1
    assert desc['name'].split('.')[-1] == 'fibonacci'
    assert desc['description'] == \
        'Compute a fibonacci number.'

    assert desc['inputs'][0]['name'] == 'n'
    assert desc['inputs'][0]['description'] == \
        'The element to return'

    assert fibonacci.call_item_task({'n': {'data': 10}}) == 55
    with pytest.raises(decorators.MissingInputException):
        fibonacci.call_item_task({})


def test_keyword_argument():
    desc = keyword_func.describe()
    assert len(desc['inputs']) == 1
    assert desc['name'].split('.')[-1] == 'keyword_func'
    assert desc['description'] == \
        'Return a value.'

    assert desc['inputs'][0]['name'] == 'val'
    assert desc['inputs'][0]['description'] == \
        'The value to return'

    assert keyword_func.call_item_task({'val': {'data': 'foo'}}) == 'foo'
    assert keyword_func.call_item_task({}) == 'test'


def test_multiple_arguments():
    desc = complex_func.describe()
    assert len(desc['inputs']) == 5
    assert desc['name'].split('.')[-1] == 'complex_func'

    assert desc['inputs'][0]['name'] == 'arg1'
    assert desc['inputs'][1]['name'] == 'arg2'
    assert desc['inputs'][2]['name'] == 'kwarg1'
    assert desc['inputs'][3]['name'] == 'kwarg2'
    assert desc['inputs'][4]['name'] == 'kwarg3'

    with pytest.raises(decorators.MissingInputException):
        complex_func.call_item_task({})

    with pytest.raises(decorators.MissingInputException):
        complex_func.call_item_task({
            'arg1': {'data': 'value'}
        })

    with pytest.raises(ValueError):
        complex_func.call_item_task({
            'arg1': {'data': 'value'},
            'arg2': {'data': 'invalid'}
        })

    with pytest.raises(TypeError):
        complex_func.call_item_task({
            'arg1': {'data': 'value'},
            'arg2': {'data': 'a'},
            'kwarg2': {'data': 'foo'}
        })

    assert complex_func.call_item_task({
        'arg1': {'data': 'value'},
        'arg2': {'data': 'a'}
    }) == {
        'arg1': 'value',
        'arg2': 'a',
        'kwarg1': ('one',),
        'kwarg2': 4,
        'kwarg3': (1, 2)
    }

    assert complex_func.call_item_task({
        'arg1': {'data': 'value'},
        'arg2': {'data': 'b'},
        'kwarg1': {'data': 'one,two'},
        'kwarg2': {'data': 10},
        'kwarg3': {'data': (1, 4)}
    }) == {
        'arg1': 'value',
        'arg2': 'b',
        'kwarg1': ['one', 'two'],
        'kwarg2': 10,
        'kwarg3': (1, 4)
    }


def test_girder_input_mode():
    item, folder = girder_types_func.call_item_task({
        'item': {
            'mode': 'girder',
            'id': 'itemid',
            'resource_type': 'item',
            'fileName': 'file.txt'
        },
        'folder': {
            'mode': 'girder',
            'id': 'folderid',
            'resource_type': 'folder'
        }
    })

    assert item == 'itemid'
    assert folder == 'folderid'


def test_missing_description_exception():
    def func():
        pass

    with pytest.raises(decorators.MissingDescriptionException):
        decorators.get_description_attribute(func)


def test_argument_name_not_string():
    with pytest.raises(TypeError):
        argument(0, types.Integer)


def test_argument_name_not_a_parameter():
    with pytest.raises(ValueError):
        @argument('notarg', types.Integer)
        def func(arg):
            pass


def test_unhandled_input_binding():
    arg = argument('arg', types.Integer)
    with pytest.raises(ValueError):
        decorators.get_input_data(arg, {})
