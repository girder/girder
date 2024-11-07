import sys


def tee_stdout(cls):
    """Decorate a Tee class giving it access to sys.stdout.

    This function is intended to decorate a class that subclasses the
    Tee object. It assigns the _set_stream and _get_stream methods on
    the cls in such a way that the class's write() method will recieve
    data passed to sys.stdout.
    """
    def _set_stdout(stream):
        """Set sys.stdout to a new file-like object.

        This is a private function for re-assigning sys.stdout. It returns
        the old value of sys.stdout.

        """
        old = sys.stdout
        sys.stdout = stream
        return old

    def _get_stdout():
        """Return the object that sys.stdout points too."""
        return sys.stdout

    cls._set_stream = staticmethod(_set_stdout)
    cls._get_stream = staticmethod(_get_stdout)

    return cls


def tee_stderr(cls):
    """Decorate a Tee class giving it access to sys.stderr.

    This function is intended to decorate a class that subclasses the
    Tee object. It assigns the _set_stream and _get_stream methods on
    the cls in such a way that the class's write() method will recieve
    data passed to sys.stderr.
    """
    def _set_stderr(stream):
        """Set sys.stderr to a new file-like object.

        This is a private function for re-assigning sys.stderr. It returns
        the old value of sys.stderr.

        """
        old = sys.stderr
        sys.stderr = stream
        return old

    def _get_stderr():
        """Return the object that sys.stderr points too."""
        return sys.stderr

    cls._set_stream = staticmethod(_set_stderr)
    cls._get_stream = staticmethod(_get_stderr)
    return cls


class Tee:
    """Implements a context manager for intercepting write streams.

    This object is loosely inspired by the classic GNU utility
    tee(1). It allows a developer to intercept stream write() calls,
    act on that data, and then passes that data through to the
    original stream object.

    Consider the case of sys.stdout; which is like a global 'pointer'
    to a writeable object. It may be reassigned to other writable
    objects to 'hijack' the effects of print() or sys.stdout.write()
    statements. This is somewhat problematic, as we may want to write
    both to the new object, and to the previous value of sys.stdout
    (e.g. a pseudo-tty).

    The Tee object implements a basic, singly-linked list of writable
    objects. When a process calls print(), data is written to
    sys.stdout, which (if it is a Tee object) calls write(), and then
    passes the data to its downstream object for processing. This
    process continues until either it encounters a non-Tee object
    (e.g. the open stdout file object) or a Tee that does not pass
    data through to its downstream connections.

    """

    # Note that by abstracting over the stream via the _set_stream and
    # _get_stream methods we can use decorators like tee_stdout and
    # tee_stderr to implement common functionality in a base class and
    # then decorate derived subclasses which handle specific stream
    # functionality. See TeeStdOut and TeeStdErr.
    @staticmethod
    def _set_stream(stream):
        """Set a stream 'pointer' (e.g. sys.stdout) to a new writeable object.

        This function should set a known global pointer to a stream
        object (e.g sys.stdout) to a new writable object. it should
        return the old value of the pointer so that it may be stored
        in the '_downstream' attribute of the Tee object.

        """
        pass

    @staticmethod
    def _get_stream():
        """Get the stream 'pointer' this object is Teeing.

        For example, if this object was Teeing sys.stdout, it would
        return the current value of sys.stdout.
        """
        pass

    def __init__(self, pass_through=True):
        self.pass_through = pass_through
        self._downstream = self._set_stream(self)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.reset()

    def reset(self):
        """Remove the current Tee object from the list of Tee objects.

        This removes the current object from the linked list of Tee
        objects associated with the stream returned by
        self._get_stream().

        Consider the case of several chained Tee objects (e.g. t1, t2,
        t3) where the original '<stdout>' open file is downstream from
        t1, t1 is downstream from t2, and t2 is downstream from t3:

        t3 => t2 => t1 => <open file '<stdout>', ...>
        ^
        sys.stdout

        sys.stdout points to t3. If we call t1.reset() it would be
        incorrect to set sys.stdout to the <open file ...> (t1's
        downstream). Instead sys.stdout must continue to point to t3
        and t2._downstream should be updated to point to the <open
        file ...>. This ensures that Tee objects may leave the chain
        as-needed without losing connections.

        """
        prev, cur = None, self._get_stream()

        if cur == self:
            self._set_stream(self._downstream)
            return

        while hasattr(cur, '_downstream'):
            prev, cur = cur, cur._downstream
            if cur == self:
                prev._downstream = cur._downstream

    def __getattr__(self, attr):
        return getattr(self._downstream, attr)

    def write(self, *args, **kwargs):
        if self.pass_through:
            self._downstream.write(*args, **kwargs)

    def flush(self, *args, **kwargs):
        if self.pass_through:
            self._downstream.flush(*args, **kwargs)


@tee_stdout
class TeeStdOut(Tee):
    pass


@tee_stderr
class TeeStdErr(Tee):
    pass
