from .choice import Choice


class StringMultichoice(Choice):
    """Define a multichose string parameter type.

    Values of this type are iterable sequences of strings
    all of which must be an element of a predefined set.

    >>> @argument('people', types.StringMultichoice, choices=('alice', 'bob', 'charlie'))
    ... def func(people=('alice', 'bob')):
    ...     pass
    """

    paramType = 'string-enumeration-multiple'
    multiple = True
