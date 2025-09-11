"""
Helper functions used by the CLI. Currently this only defines
:class:`_JSONEmitter`, which we test here.

Example:
    >>> from girder_client.util import _JSONEmitter
    >>> import io
    >>> self = _JSONEmitter(stream=io.StringIO())
    >>> self.start_dict()
    >>> self.setitem('version', '1.0.0')
    >>> self.start_subcontainer('info')
    >>> self.start_list()
    >>> self.append({})
    >>> self.append([{}])
    >>> self.append({})
    >>> self.end_list()
    >>> self.end_dict()
    >>> text = self.stream.getvalue()
    >>> # Test that we decode correctly
    >>> import json as json
    >>> print(json.loads(text))
    {'version': '1.0.0', 'info': [{}, [{}], {}]}

Example:
    >>> from girder_client.util import _JSONEmitter
    >>> import io
    >>> self = _JSONEmitter(stream=io.StringIO())
    >>> self.start_dict()
    >>> self.setitem('key1', 'value1')
    >>> self.start_subcontainer('subdict1')
    >>> self.start_dict()
    >>> self.end_dict()
    >>> #
    >>> self.start_subcontainer('subdict2')
    >>> self.start_dict()
    >>> self.setitem('subkey1', 'subvalue1')
    >>> self.setitem('subkey2', 'subvalue2')
    >>> self.setitem('subkey3', [1, 2, 3, {"a": "a"}])
    >>> self.end_dict()
    >>> #
    >>> self.start_subcontainer('sublist')
    >>> self.start_list()
    >>> self.append('sublist_value1')
    >>> self.append('sublist_value2')
    >>> self.append([1, 2, 3, {"a": "a"}])
    >>> self.end_list()
    >>> #
    >>> self.setitem('key2', 'value2')
    >>> self.end_dict()
    >>> #
    >>> text = self.stream.getvalue()
    >>> # Test that we decode correctly
    >>> import json
    >>> print(json.dumps(json.loads(text)))
"""
import json


class _AssertionMixin:
    """
    Assertion / check boilerplate is useful to have, but keeping it separated
    from the core logic to reduce clutter in the main class.
    """

    def _assert_number_of_toplevel_containers_le_1(self, context):
        if context['type'] == 'root' and context['size'] > 1:
            raise AssertionError('Top level can only contain one container')

    def _assert_subcontainer_is_prepared(self, context):
        if not context.get('subcontainer_prepared', False):
            raise AssertionError(
                "Expected that a subcontainer IS prepared, but it wasn't"
                f'context={context}'
            )

    def _assert_subcontainer_is_not_prepared(self, context):
        if context.get('subcontainer_prepared', False):
            raise AssertionError(
                'Expected that a subcontainer is NOT prepared, but it was'
                f'context={context}'
            )

    def _assert_context_type_eq(self, context, expected_type):
        if context['type'] != expected_type:
            raise AssertionError(
                f'Expected type == {expected_type}, but got context={context}'
            )

    def _assert_context_type_ne(self, context, expected_type):
        if context['type'] == expected_type:
            raise AssertionError(
                f'Expected type != {expected_type}, but got context={context}'
            )


class _JSONEmitter(_AssertionMixin):
    """
    Helps incrementally emit compliant JSON text.

    Useful when the data to serialize is slowly streaming in and minimal
    response time is desired.

    Example:
        >>> from girder_client.util import *  # NOQA
        >>> self = _JSONEmitter()
        >>> self.start_dict()
        >>> self.end_dict()
        {}
        >>> self = _JSONEmitter()
        >>> self.start_dict()
        >>> self.setitem('k1', 'v1')
        >>> self.setitem('k2', 'v2')
        >>> self.setitem('k3', 'v3')
        >>> self.end_dict()
    """
    def __init__(self, stream=None, checks=True, ):
        """
        Args:
            stream (io._io._TextIOBas): stream to write to (defaults to stdout)
            checks (bool): if True checks that operations are legal
        """
        import sys
        self._stack = [{'type': 'root', 'depth': -1, 'size': 0}]
        if stream is None:
            stream = sys.stdout
        self.stream = stream
        self.checks = checks

    def _ensure_separator(self, context):
        """
        Prepare for an increase in length to the current container.

        Use when you are about to add a new item that would increase the
        length of the container. If it is the first items in this container,
        we do not write a trailing comma, otherwise we know the container is
        not empty, and we need to add a trailing comma for the previous item.
        TODO: handle indentation
        """
        # If a subcontainer was prepared, it already called this.
        if context.pop('subcontainer_prepared', False):
            return
        if context['size'] == 0:
            self.stream.write('\n')
        else:
            self.stream.write(',\n')  # trailing comma for previous item
        context['size'] += 1

    def start_list(self):
        """
        Start a new list context. Must be in a list, or in a dict with a
        prepared subcontainer.
        """
        context = self._stack[-1]
        if self.checks:
            self._assert_number_of_toplevel_containers_le_1(context)
            if context['type'] == 'dict':
                self._assert_subcontainer_is_prepared(context)

        self._ensure_separator(context)

        self._stack.append({'type': 'list', 'size': 0, 'depth': context['depth'] + 1})
        self.stream.write('[')

    def start_dict(self):
        """
        Start a new dictionary context. Must be in a list, or in a dict with a
        prepared subcontainer.
        """
        context = self._stack[-1]
        if self.checks:
            self._assert_number_of_toplevel_containers_le_1(context)
            if context['type'] == 'dict':
                self._assert_subcontainer_is_prepared(context)

        self._ensure_separator(context)

        self._stack.append({'type': 'dict', 'size': 0, 'depth': context['depth'] + 1})
        self.stream.write('{')

    def end_list(self):
        """
        End the current list context.
        """
        context = self._stack.pop()
        if self.checks:
            self._assert_subcontainer_is_not_prepared(context)
            self._assert_context_type_eq(context, 'list')
        if context['size'] > 0:
            self.stream.write('\n')
        self.stream.write(']')

    def end_dict(self):
        """
        End the current dictionary context
        """
        context = self._stack.pop()
        if self.checks:
            self._assert_subcontainer_is_not_prepared(context)
            self._assert_context_type_eq(context, 'dict')
        if context['size'] > 0:
            self.stream.write('\n')
        self.stream.write('}')

    def start_subcontainer(self, key):
        """
        Add a key to a dictionary whose value will be a new container.

        Args:
            key: the key that maps to the new subcontainer

        Can only be called if you are inside a dict context.
        The next call must start a new dict or list container.
        """
        context = self._stack[-1]
        if self.checks:
            self._assert_context_type_eq(context, 'dict')
            self._assert_subcontainer_is_not_prepared(context)

        self._ensure_separator(context)
        self.stream.write(json.dumps(key) + ': ')
        context['subcontainer_prepared'] = True

    def setitem(self, key, value):
        """
        Add an item to a dict context.

        Args:
            key (str): a string key
            value (Any): any json serializable object.
        """
        context = self._stack[-1]
        if self.checks:
            self._assert_context_type_eq(context, 'dict')
            self._assert_subcontainer_is_not_prepared(context)

        self._ensure_separator(context)
        self.stream.write(json.dumps(key))
        self.stream.write(': ')
        self.stream.write(json.dumps(value))

    def append(self, item):
        """
        Add an item to a list context

        Args:
            item (Any): a json serializable object
        """
        context = self._stack[-1]
        if self.checks:
            self._assert_context_type_eq(context, 'list')
        self._ensure_separator(context)
        self.stream.write(json.dumps(item))
