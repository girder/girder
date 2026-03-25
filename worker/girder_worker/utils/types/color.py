from .base import Base


class Color(Base):
    """Define a task parameter expecting a color value.

    >>> @argument('background', types.Color)
    ... def func(background):
    ...     pass
    """

    description = {
        'type': 'color',
        'description': 'Provide a color value'
    }

    # TODO: handle normalization and validation
