from .number import Number


class Range(Number):
    """Define numeric parameter with valid values in a given range.

    >>> @argument('value', types.Range, min=10, max=100, step=10)
    ... def func(value):
    ...     pass
    """

    paramType = 'range'
