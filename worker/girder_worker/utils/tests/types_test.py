import pytest

from girder_worker_utils import types


def test_serialize_boolean():
    arg = types.Boolean('arg')
    assert arg.serialize(None) is False
    assert arg.serialize(1) is True


def test_validate_choice_value():
    arg = types.StringMultichoice('arg')
    with pytest.raises(TypeError):
        arg.validate('not a list')


def test_serialize_integer():
    arg = types.Integer('arg')
    assert arg.serialize(1.0) == 1


def test_validate_integer_range():
    arg = types.Integer('arg', min=0, max=10)
    with pytest.raises(ValueError):
        arg.validate(-1)

    with pytest.raises(ValueError):
        arg.validate(11)


def test_validate_string():
    arg = types.String('arg')
    with pytest.raises(TypeError):
        arg.validate(1)


def test_validate_number_vector():
    arg = types.NumberVector('arg')
    with pytest.raises(TypeError):
        arg.validate('not a list')
