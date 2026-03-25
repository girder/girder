from .string import String
from .vector import Vector


class StringVector(Vector):
    """Define a parameter which takes a list of strings.

    >>> @argument('people', types.StringVector)
    ... def func(people=('alice', 'bob')):
    ...     pass
    """

    paramType = 'string-vector'
    elementClass = String
