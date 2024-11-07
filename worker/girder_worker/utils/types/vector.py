from .base import Base


class Vector(Base):
    """Define a base class that accepts an iterable object."""

    #: The explicit type provided by the subclass
    paramType = None

    #: The class of the elements of the vector
    elementClass = None

    #: A list seperator for serialization
    seperator = ','

    def __init__(self, *args, **kwargs):
        if self.paramType is None:  # pragma: nocover
            raise NotImplementedError('Subclasses should define paramType')

        if self.elementClass is None:  # pragma: nocover
            raise NotImplementedError('Subclasses should define elementClass')

        self.element = self.elementClass(*args, **kwargs)
        super().__init__(*args, **kwargs)

    def describe(self, *args, **kwargs):
        desc = super().describe(*args, **kwargs)
        desc['type'] = self.paramType
        desc['description'] = 'Provide a list of values'
        return desc

    def validate(self, value):
        if not isinstance(value, (list, tuple)):
            raise TypeError('Expected a list or tuple for "%s"' % self.name)

        for elementValue in value:
            self.element.validate(elementValue)

    def deserialize(self, value):
        if isinstance(value, str):
            value = value.split(self.seperator)

        return [self.element.deserialize(v) for v in value]
