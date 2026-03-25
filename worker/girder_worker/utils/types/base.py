from copy import deepcopy


class Base:
    """Define an abstract type class.

    This class defines the interface expected by the functions in
    :py:mod:`girder_worker.describe`.  All autodescribing parameter
    types should derive from this class.
    """

    #: This is used as a base description object for all types.
    description = {}

    def __init__(self, name, **kwargs):
        """Construct a task description.

        Subclasses can define additional keyword arguments.

        :param str name: The argument name in the task function.
        :param str id: An optional id (defaults to the argument name)
        :param str help: A help string (defaults to the function docstring)
        """
        self.id = kwargs.get('id', name)
        self.name = name
        self.help = kwargs.get('help')

    def set_parameter(self, parameter, **kwargs):
        """Store a parameter instance from a function signature.

        This method is called internally by description decorators.

        :param parameter: The parameter signature from the task
        :type parameter: inspect.Parameter
        """
        self.parameter = parameter

    def has_default(self):
        """Return true if the parameter has a default value."""
        return self.parameter.default is not self.parameter.empty

    def describe(self):
        """Return a type description serialization."""
        copy = deepcopy(self.description)
        copy.setdefault('id', self.id)
        copy.setdefault('name', self.name)
        if self.has_default():
            copy.setdefault('default', {
                'data': self.serialize(self.parameter.default)
            })
        if self.help is not None:
            copy['description'] = self.help
        return copy

    def serialize(self, value):
        """Serialize a python value into a format expected by item_tasks."""
        return value

    def deserialize(self, value):
        """Deserialize a python value from a format provided by item_tasks."""
        return value

    def validate(self, value):
        """Validate a parameter value.

        :raises Exception: if the value is not valid
        """
