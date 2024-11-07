from .base import Base


class String(Base):
    """Define a parameter that can be an arbitrary string.

    >>> @argument('person', types.String)
    ... def func(person='eve'):
    ...     pass
    """

    description = {
        'type': 'string',
        'description': 'Provide a string value'
    }

    def validate(self, value):
        if not isinstance(value, str):
            raise TypeError('Expected a string value for "%s"' % self.name)
