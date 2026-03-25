from .number import Number


class Integer(Number):
    """Define an integer task parameter.

    >>> @argument('iterations', types.Integer)
    ... def func(iterations=3):
    ...     pass
    """

    paramType = 'integer'

    def __init__(self, *args, **kwargs):
        kwargs['step'] = 1
        super().__init__(*args, **kwargs)

    def serialize(self, value):
        value = super().serialize(value)
        return int(value)
