from .base import Base


class Boolean(Base):
    """Define a boolean task parameter.

    >>> @argument('debug', types.Boolean)
    ... def func(debug=False):
    ...     pass
    """

    description = {
        'type': 'boolean',
        'description': 'Provide a boolean value'
    }

    def serialize(self, value):
        return bool(value)
