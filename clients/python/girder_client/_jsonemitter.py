"""
Helper functions used by the CLI. Currently this only defines
:class:`_JSONEmitter`, which we test here.

Example:
    >>> from girder_client._jsonemitter import _JSONEmitter
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
    >>> from girder_client._jsonemitter import _JSONEmitter
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

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Literal, TextIO

__all__ = ['_JSONEmitter']

_ContainerKind = Literal['root', 'dict', 'list']


@dataclass
class _Context:
    """State for one open JSON container."""

    kind: _ContainerKind
    size: int = 0
    awaiting_subcontainer: bool = False


class _JSONEmitter:
    """
    Helps incrementally emit compliant JSON text.

    Useful when the data to serialize is slowly streaming in and minimal
    response time is desired.

    Example:
        >>> from girder_client._jsonemitter import *  # NOQA
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

    def __init__(self, stream: TextIO | None = None, checks: bool = True) -> None:
        """
        Args:
            stream: stream to write to (defaults to stdout)
            checks: if True checks that operations are legal
        """
        self._stack: list[_Context] = [_Context('root')]
        self.stream: TextIO = sys.stdout if stream is None else stream
        self.checks: bool = checks

    def _current(self) -> _Context:
        """Return the current container context."""
        return self._stack[-1]

    def _assert_can_start_container(self, context: _Context) -> None:
        """Validate that a new dict/list value may start in ``context``."""
        if context.kind == 'root':
            if context.size >= 1:
                raise AssertionError('Top level can only contain one container')
        elif context.kind == 'dict':
            if not context.awaiting_subcontainer:
                raise AssertionError(
                    'Expected start_subcontainer(key) before starting a '
                    f'nested container; context={context!r}'
                )
        elif context.kind != 'list':
            raise AssertionError(f'Unknown container context={context!r}')

    def _assert_can_write_dict_item(self, context: _Context) -> None:
        """Validate that a plain key/value item may be written to a dict."""
        if context.kind != 'dict':
            raise AssertionError(
                f"Expected current context to be 'dict', but got context={context!r}"
            )
        if context.awaiting_subcontainer:
            raise AssertionError(
                'Expected a nested dict/list after start_subcontainer(key), '
                f'but got a plain dict item; context={context!r}'
            )

    def _assert_can_write_list_item(self, context: _Context) -> None:
        """Validate that a plain value may be appended to a list."""
        if context.kind != 'list':
            raise AssertionError(
                f"Expected current context to be 'list', but got context={context!r}"
            )

    def _prepare_value(self, context: _Context) -> None:
        """
        Write any separator needed before emitting the next JSON value.

        ``start_subcontainer`` writes a dict key before the corresponding
        container exists. In that one case, the dict item has already been
        counted and separated, so starting the child container consumes the
        pending state without writing another separator.
        """
        if context.awaiting_subcontainer:
            context.awaiting_subcontainer = False
            return

        if context.size > 0:
            self.stream.write(',\n')
        elif context.kind != 'root':
            self.stream.write('\n')
        context.size += 1

    def _start_container(self, kind: _ContainerKind, opener: str) -> None:
        """Start a new list or dict container."""
        context = self._current()
        if self.checks:
            self._assert_can_start_container(context)

        self._prepare_value(context)
        self.stream.write(opener)
        self._stack.append(_Context(kind))

    def _end_container(self, expected_kind: _ContainerKind, closer: str) -> None:
        """End the current list or dict container."""
        if len(self._stack) == 1:
            raise AssertionError('No open container to end')

        context = self._current()
        if self.checks:
            if context.awaiting_subcontainer:
                raise AssertionError(
                    'Expected a nested dict/list after start_subcontainer(key), '
                    f'but the {context.kind!r} context is ending; context={context!r}'
                )
            if context.kind != expected_kind:
                raise AssertionError(
                    f'Expected current context to be {expected_kind!r}, '
                    f'but got context={context!r}'
                )

        self._stack.pop()
        if context.size > 0:
            self.stream.write('\n')
        self.stream.write(closer)

    def start_list(self) -> None:
        """
        Start a new list context. Must be in a list, or in a dict with a
        prepared subcontainer.
        """
        self._start_container('list', '[')

    def start_dict(self) -> None:
        """
        Start a new dictionary context. Must be in a list, or in a dict with a
        prepared subcontainer.
        """
        self._start_container('dict', '{')

    def end_list(self) -> None:
        """End the current list context."""
        self._end_container('list', ']')

    def end_dict(self) -> None:
        """End the current dictionary context."""
        self._end_container('dict', '}')

    def start_subcontainer(self, key: str) -> None:
        """
        Add a key to a dictionary whose value will be a new container.

        Args:
            key: the key that maps to the new subcontainer

        Can only be called if you are inside a dict context.
        The next call must start a new dict or list container.
        """
        context = self._current()
        if self.checks:
            self._assert_can_write_dict_item(context)

        self._prepare_value(context)
        self.stream.write(json.dumps(key))
        self.stream.write(': ')
        context.awaiting_subcontainer = True

    def setitem(self, key: str, value: Any) -> None:
        """
        Add an item to a dict context.

        Args:
            key: a string key
            value: any JSON-serializable object
        """
        context = self._current()
        if self.checks:
            self._assert_can_write_dict_item(context)

        self._prepare_value(context)
        self.stream.write(json.dumps(key))
        self.stream.write(': ')
        self.stream.write(json.dumps(value))

    def append(self, item: Any) -> None:
        """
        Add an item to a list context.

        Args:
            item: any JSON-serializable object
        """
        context = self._current()
        if self.checks:
            self._assert_can_write_list_item(context)

        self._prepare_value(context)
        self.stream.write(json.dumps(item))
