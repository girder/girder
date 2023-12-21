_validators = {}
_defaultFunctions = {}


def registerValidator(key, fn, replace=False):
    """
    Register a validator for a given setting key.

    :param key: The setting key.
    :type key: str
    :param fn: The function that will validate this key.
    :type fn: callable
    :param replace: If a validator already exists for this key, set this to True to replace the
        existing validator. The default is to add the new validator in addition to running the
        old validation function.
    :type replace: bool
    """
    if not replace and key in _validators:
        old = _validators[key]

        def wrapper(doc):
            fn(doc)
            old(doc)
        _validators[key] = wrapper
    else:
        _validators[key] = fn


def getValidator(key):
    """
    Retrieve the validator function for the given key. Returns ``None`` if none is registered.
    """
    return _validators.get(key)


def registerDefaultFunction(key, fn):
    """
    Register a default value function for a given setting key.

    :param key: The setting key.
    :type key: str
    :param fn: The function that will return the default value for this key.
    :type fn: callable
    """
    _defaultFunctions[key] = fn


def getDefaultFunction(key):
    """
    Retrieve the default value function for the given key. Returns ``None`` if none is registered.
    """
    return _defaultFunctions.get(key)


class validator:  # noqa: class name
    """
    Create a decorator indicating that the wrapped function is responsible for
    validating the given key or set of keys. For example,

    >>> @validator('my_plugin.setting_key')
    >>> def validateMySetting(doc):
    >>>     if not doc['value']:
    >>>         raise ValidationException('This key must not be empty.')

    :param key: The key(s) that this function validates.
    :type key: str or iterable of str
    :param replace: If a validator already exists for this key, set this to True to replace the
        existing validator. The default is to add the new validator in addition to running the
        old validation function.
    :type replace: bool
    """

    def __init__(self, key, replace=False):
        if isinstance(key, str):
            key = {key}
        self.keys = key
        self.replace = replace

    def __call__(self, fn):
        for k in self.keys:
            registerValidator(k, fn, replace=self.replace)
        return fn


class default:  # noqa: class name
    """
    Create a decorator indicating that the wrapped function is responsible for
    providing the default value for the given key or set of keys.

    :param key: The key(s) that this function validates.
    :type key: str or iterable of str
    """

    def __init__(self, key):
        if isinstance(key, str):
            key = {key}
        self.keys = key

    def __call__(self, fn):
        for k in self.keys:
            registerDefaultFunction(k, fn)
        return fn
