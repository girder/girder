import time

from girder.exceptions import ValidationException, RestException
from girder.notification import Notification, ProgressState


class ProgressContext:
    """
    This class is a context manager that can be used to update progress in a way
    that rate-limits writes to the database and guarantees a flush when the
    context is exited. This is a no-op if "on" is set to False, which is
    meant as a convenience for callers. Any additional kwargs passed to this
    constructor are passed through to the ``initProgress`` method of the
    notification model.

    :param on: Whether to record progress.
    :type on: bool
    :param interval: Minimum time interval at which to write updates to the
        database, in seconds.
    :type interval: int or float
    :param user: The user creating this progress.
    :type user: dict
    :param title: The title for the task being tracked.
    :type title: str
    """

    def __init__(self, on, interval=0.5, **kwargs):
        self.on = on
        self.interval = interval
        self._lastFlush = time.time()

        if on:
            self.progress = Notification.initProgress(**kwargs)

    def __enter__(self):
        return self

    def __exit__(self, excType, excValue, traceback):
        if not self.on:
            return

        if excType is None and excValue is None:
            state = ProgressState.SUCCESS
            message = 'Done'
        else:
            state = ProgressState.ERROR
            message = 'Error'
            if isinstance(excValue, (ValidationException, RestException)):
                message = 'Error: ' + str(excValue)

        self.progress.updateProgress(state=state, message=message)

    def update(self, force: bool = False, increment: int = None, **kwargs):
        """
        Update the underlying progress record. This will only actually save
        to the database if at least self.interval seconds have passed since
        the last time the record was written to the database. Accepts the
        same kwargs as Notification.updateProgress.

        :param force: Whether we should force flushing the message, even if the minimum interval
            has not passed.
        :param increment: The amount to increment the current progress by.
        """
        if not self.on:
            return

        if (time.time() - self._lastFlush > self.interval) or force:
            self._lastFlush = time.time()
            self.progress.updateProgress(increment=increment, **kwargs)


noProgress = ProgressContext(on=False)
