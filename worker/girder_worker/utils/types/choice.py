from .base import Base


class Choice(Base):
    """Define base functionality for multi choice parameter."""

    #: The explicit type provided by the subclass
    paramType = None

    #: Whether the parameter accepts multiple values from the choices
    multiple = False

    def __init__(self, *args, **kwargs):
        """Construct a choice parameter.

        :param list choices: A list of valid values.
        """
        self.choices = kwargs.get('choices', [])
        super().__init__(*args, **kwargs)

    def describe(self, *args, **kwargs):
        desc = super().describe(*args, **kwargs)
        desc['type'] = self.paramType
        desc['values'] = self.choices
        desc['description'] = 'Choose from a list of values'
        return desc

    def _validate_one(self, value):
        if value not in self.choices:
            raise ValueError('Invalid value provided for "%s"' % self.name)

    def validate(self, value):
        if not self.multiple:
            value = [value]

        if not isinstance(value, (list, tuple)):
            raise TypeError(
                'Expected a list or tuple for "%s"' % self.name)
        for v in value:
            self._validate_one(v)
