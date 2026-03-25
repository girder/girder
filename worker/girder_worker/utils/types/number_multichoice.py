from .choice import Choice


class NumberMultichoice(Choice):
    """Define a multichose numeric parameter type.

    Values of this type are iterable sequences of numbers
    all of which must be an element of a predefined set.

    >>> @argument('images', types.NumberMultichoice, choices=(5, 10, 15))
    ... def func(images=(5, 10)):
    ...     pass
    """

    paramType = 'number-enumeration-multiple'
    multiple = True
