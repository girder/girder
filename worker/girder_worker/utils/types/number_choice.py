from .choice import Choice


class NumberChoice(Choice):
    """Define a numeric parameter with a set of valid values.

    >>> @argument('address', types.NumberChoice, choices=(5, 10, 15))
    ... def func(address):
    ...     pass
    """

    paramType = 'number-enumeration'
