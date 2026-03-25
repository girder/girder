from .choice import Choice


class StringChoice(Choice):
    """Define a string parameter with a list of valid values.

    >>> @argument('person', types.StringChoice, choices=('alice', 'bob', 'charlie'))
    ... def func(person):
    ...     pass
    """

    paramType = 'string-enumeration'
