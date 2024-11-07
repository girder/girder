import jsonpickle
import pytest


from girder_worker_utils.transform import Transform


class CaptureTransform(Transform):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def transform(self):
        return self.args, self.kwargs


class BasicCustomTransform(Transform):
    def __init__(self, arg1, kwarg1=None):
        self.arg1 = arg1
        self.kwarg1 = kwarg1

    def transform(self):
        return None


class ComputedCustomTransform(Transform):
    def __init__(self, kwarg1=None):
        if kwarg1 is None:
            self.kwarg1 = 'COMPUTED VALUE'

    def transform(self):
        return None


class CustomSerializeTransform(Transform):
    def __init__(self, arg1, kwarg1='some_value'):
        self.arg1 = arg1
        self.kwarg1 = kwarg1

    def __getstate__(self):
        return {'some_attr': 'some_value'}

    def transform(self):
        return None


def test_instantiate_transform_behavior():
    with pytest.raises(TypeError):
        Transform()


def test_basic_transform_behavior():
    assert CaptureTransform().transform() == ((), {})


def test_noop_transform():
    assert CaptureTransform('some value').transform() == (('some value', ), {})


def test_non_hook_transform_roundtrip():
    obj = {'key': 'value',
           'key2': ['list', 'of', 'values'],
           'key3': {'inner': 'dict'}}

    ret = jsonpickle.decode(jsonpickle.encode(obj))
    assert ret == obj


def test_transform_serialize_roundtrip():
    args = ('arg1', 'arg2', 'arg3')
    kwargs = {'kwarg1': 'kwarg1', 'kwarg2': 'kwarg2'}
    original_instance = CaptureTransform(*args, **kwargs)
    new_instance = jsonpickle.decode(jsonpickle.encode(original_instance))

    assert isinstance(new_instance, Transform)
    assert new_instance.args == args
    assert new_instance.kwargs == kwargs


def test_basic_custom_transform_arg1_roundtrip():
    new_instance = jsonpickle.decode(jsonpickle.encode(
        BasicCustomTransform('some_value')
    ))

    assert isinstance(new_instance, BasicCustomTransform)
    assert new_instance.arg1 == 'some_value'


def test_basic_custom_transform_kwarg1_None_roundtrip():
    new_instance = jsonpickle.decode(jsonpickle.encode(
        BasicCustomTransform(None)
    ))

    assert isinstance(new_instance, BasicCustomTransform)
    assert new_instance.kwarg1 is None


def test_basic_custom_transform_kwarg1_not_None_roundtrip():
    new_instance = jsonpickle.decode(jsonpickle.encode(
        BasicCustomTransform(None, kwarg1='some_value')
    ))

    assert isinstance(new_instance, BasicCustomTransform)
    assert new_instance.kwarg1 == 'some_value'


def test_computed_custom_transform_kwarg1_has_computed_value_roundtrip():
    new_instance = jsonpickle.decode(jsonpickle.encode(
        ComputedCustomTransform()
    ))

    assert isinstance(new_instance, ComputedCustomTransform)
    assert new_instance.kwarg1 == 'COMPUTED VALUE'


def test_custom_serialize_transform_has_correct_attrs_roundtrip():
    new_instance = jsonpickle.decode(jsonpickle.encode(
        CustomSerializeTransform('arg1', 'kwarg1')
    ))

    assert isinstance(new_instance, CustomSerializeTransform)
    assert not hasattr(new_instance, 'arg1')
    assert not hasattr(new_instance, 'kwarg1')
    assert hasattr(new_instance, 'some_attr')
    assert new_instance.some_attr == 'some_value'
