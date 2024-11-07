from inspect import getdoc
try:
    from inspect import signature
except ImportError:  # pragma: nocover
    from funcsigs import signature


class MissingDescriptionException(Exception):
    """Raised when a function is missing description decorators."""


class MissingInputException(Exception):
    """Raised when a required input is missing."""


def get_description_attribute(func):
    """Get the private description attribute from a function."""
    func = getattr(func, 'run', func)
    description = getattr(func, '_girder_description', None)
    if description is None:
        raise MissingDescriptionException('Function is missing description decorators')
    return description


def argument(name, data_type, *args, **kwargs):
    """Describe an argument to a function as a function decorator.

    Additional arguments are passed to the type class constructor.

    :param str name: The parameter name from the function declaration
    :param type: A type class derived from ``girder_worker_utils.types.Base``
    """
    if not isinstance(name, str):
        raise TypeError('Expected argument name to be a string')

    if callable(data_type):
        data_type = data_type(name, *args, **kwargs)

    def argument_wrapper(func):
        func._girder_description = getattr(func, '_girder_description', {})
        args = func._girder_description.setdefault('arguments', [])
        sig = signature(func)

        if name not in sig.parameters:
            raise ValueError('Invalid argument name "%s"' % name)

        data_type.set_parameter(sig.parameters[name], signature=sig)
        args.insert(0, data_type)

        def call_item_task(inputs, outputs=None):
            args, kwargs = parse_inputs(func, inputs)
            return func(*args, **kwargs)

        def describe():
            return describe_function(func)

        func.call_item_task = call_item_task
        func.describe = describe

        return func

    return argument_wrapper


def describe_function(func):
    """Return a json description from a decorated function."""
    description = get_description_attribute(func)

    inputs = [arg.describe() for arg in description.get('arguments', [])]
    spec = {
        'name': description.get('name', func.__name__),
        'inputs': inputs,
        'mode': 'girder_worker'
    }
    desc = description.get('description', getdoc(func))
    if desc:
        spec['description'] = desc

    return spec


def get_input_data(arg, input_binding):
    """Parse an input binding from a function argument description.

    :param arg: An instantiated type description
    :param input_binding: An input binding object
    :returns: The parameter value
    """
    mode = input_binding.get('mode', 'inline')
    if mode == 'inline' and 'data' in input_binding:
        value = arg.deserialize(input_binding['data'])
    elif mode == 'girder':
        value = input_binding.get('id')
    else:
        raise ValueError('Unhandled input mode')

    arg.validate(value)
    return value


def parse_inputs(func, inputs):
    """Parse an object of input bindings from item_tasks.

    :param func: The task function
    :param dict inputs: The input task bindings object
    :returns: args and kwargs objects to call the function with
    """
    description = get_description_attribute(func)
    arguments = description.get('arguments', [])
    args = []
    kwargs = {}
    for arg in arguments:
        desc = arg.describe()
        input_id = desc['id']
        name = desc['name']
        if input_id not in inputs and not arg.has_default():
            raise MissingInputException('Required input "%s" not provided' % name)
        if input_id in inputs:
            kwargs[name] = get_input_data(arg, inputs[input_id])
    return args, kwargs
