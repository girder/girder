import numbers

from .base import Base


class Number(Base):
    """Define a numeric parameter type optionally in a given range.

    Values accepted by this parameter can be any numeric value.
    If min/max/step are provided, then the values must be a float
    or int.

    >>> @argument('value', types.Number, min=10, max=100, step=10)
    ... def func(value):
    ...     pass
    """

    paramType = 'number'

    def __init__(self, *args, **kwargs):
        """Construct a new numeric parameter type.

        :param float min: The minimum valid value
        :param float max: The maximum valid value
        :param float step: The resolution of valid values
        """
        super().__init__(*args, **kwargs)
        self.min = kwargs.get('min')
        self.max = kwargs.get('max')
        self.step = kwargs.get('step')

    def describe(self, **kwargs):
        desc = super().describe(**kwargs)

        if self.min is not None:
            desc['min'] = self.min
        if self.max is not None:
            desc['max'] = self.max
        if self.step is not None:
            desc['step'] = self.step

        desc['type'] = self.paramType
        desc['description'] = self.help or 'Select a number'
        return desc

    def validate(self, value):
        if not isinstance(value, numbers.Number):
            raise TypeError('Expected a number for parameter "%s"' % self.name)

        if self.min is not None and value < self.min:
            raise ValueError('Expected %s <= %s' % (str(self.min), str(value)))

        if self.max is not None and value > self.max:
            raise ValueError('Expected %s >= %s' % (str(self.max), str(value)))

    def serialize(self, value):
        if self.step is not None:
            n = round(float(value) / self.step)
            value = n * self.step
        return value

    def deserialize(self, value):
        try:
            value = float(value)
        except ValueError:
            pass
        return value
