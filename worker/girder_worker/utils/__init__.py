import importlib.metadata
import os
import time

import requests
# Disable urllib3 warnings about certificate validation. As they are printed in the console, the
# messages are sent to Girder, creating an infinite loop.
import urllib3
from girder_worker import logger
from requests import HTTPError

from .tee import Tee, tee_stderr, tee_stdout

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    __version__ = importlib.metadata.version(__name__)
except importlib.metadata.PackageNotFoundError:
    # package is not installed
    pass

# Per-worker override for the Girder API URL used when calling back to the server.
# When set, this takes precedence over the girder_api_url header attached at schedule time.
GIRDER_WORKER_API_URL_ENV = 'GIRDER_WORKER_API_URL'


def resolve_girder_api_url(api_url=None):
    """Resolve the Girder API URL, preferring a per-worker environment override.

    When a job is scheduled, the Girder server attaches a ``girder_api_url`` header
    based on its own view of the API root. Workers that run in a different network
    context (for example inside Docker, or on a remote host) can set
    ``GIRDER_WORKER_API_URL`` so callbacks use a URL reachable from that worker
    instead of the URL provided by the scheduling server.

    Called with no argument (or ``None``), this returns the override value alone,
    or ``None`` if the environment variable is unset.

    :param api_url: The API URL from the task headers / scheduling server.
    :type api_url: str or None
    :returns: The override URL if ``GIRDER_WORKER_API_URL`` is set, otherwise
        ``api_url``.
    :rtype: str or None
    """
    return os.environ.get(GIRDER_WORKER_API_URL_ENV) or api_url


def rewrite_url_api_base(url, original_api_url, new_api_url):
    """Rewrite a URL that starts with ``original_api_url`` to use ``new_api_url``.

    Used to update embedded job callback URLs (for example in ``jobInfoSpec``)
    when a worker overrides the Girder API base URL.

    :param url: A full URL that may begin with ``original_api_url``.
    :type url: str or None
    :param original_api_url: The API base URL originally embedded in ``url``.
    :type original_api_url: str or None
    :param new_api_url: The API base URL that should replace ``original_api_url``.
    :type new_api_url: str or None
    :returns: The rewritten URL, or ``url`` unchanged if a rewrite is not possible.
        When ``url`` and ``new_api_url`` are set but ``original_api_url`` is
        missing, a warning is logged and ``url`` is returned unchanged.
    :rtype: str or None
    """
    if not url or not new_api_url:
        return url
    if not original_api_url:
        logger.warning(
            'Cannot rewrite API URL %r to %r because the original API base URL '
            'is missing; leaving the URL unchanged.',
            url, new_api_url)
        return url
    original = original_api_url.rstrip('/')
    replacement = new_api_url.rstrip('/')
    if url.startswith(original):
        return replacement + url[len(original):]
    return url


def apply_girder_api_url_override(request):
    """Apply ``GIRDER_WORKER_API_URL`` to a Celery task request in place.

    Updates ``girder_api_url`` (and legacy ``apiUrl`` when present) on the request,
    and rewrites the ``jobInfoSpec`` callback URL so job status/log updates use the
    overridden API base.

    :param request: The Celery task request / context object.
    :returns: The resolved API URL after applying any override, or ``None``.
    :rtype: str or None
    """
    original_api_url = getattr(request, 'girder_api_url', None)
    if original_api_url is None:
        original_api_url = getattr(request, 'apiUrl', None)

    override = resolve_girder_api_url()
    if not override:
        return original_api_url

    if hasattr(request, 'jobInfoSpec') and request.jobInfoSpec:
        jobSpec = dict(request.jobInfoSpec)
        if 'url' in jobSpec:
            jobSpec['url'] = rewrite_url_api_base(
                jobSpec['url'], original_api_url, override)
            request.jobInfoSpec = jobSpec

    request.girder_api_url = override
    if hasattr(request, 'apiUrl'):
        request.apiUrl = override

    return override


def _walk_obj(obj, func, leaf_condition=None):
    """Walk through a nested object applying func to each leaf element.

    This function returns a recursively built structure from a nested
    tree of simple container types (e.g. dict, list, tuple) by
    applying func to each leaf node in the tree. By default a leaf
    node is considered to be any object that is not a dict, list or
    tuple.

    leaf_condition may be used if certain types of lists, tuples or
    dicts should be considered leaf nodes. leaf_condition should be
    passed a function that takes a sub-tree and returns True if that
    sub-tree is a leaf node, or False if _walk_obj should continue to
    descend through the sub-tree.

    """
    if callable(leaf_condition):
        if leaf_condition(obj):
            return func(obj)

    if isinstance(obj, dict):
        return {k: _walk_obj(v, func, leaf_condition=leaf_condition)
                for k, v in obj.items()}

    elif isinstance(obj, list):
        return [_walk_obj(v, func, leaf_condition=leaf_condition) for v in obj]

    elif isinstance(obj, tuple):
        return tuple(_walk_obj(list(obj), func, leaf_condition=leaf_condition))

    return func(obj)


BUILTIN_CELERY_TASKS = [
    'celery.accumulate'
    'celery.backend_cleanup',
    'celery.chain',
    'celery.chord',
    'celery.chord_unlock',
    'celery.chunks',
    'celery.group',
    'celery.map',
    'celery.starmap']


def is_builtin_celery_task(task):
    return task in BUILTIN_CELERY_TASKS


def _maybe_model_repr(obj):
    if hasattr(obj, '_repr_model_') and callable(obj._repr_model_):
        return obj._repr_model_()
    return obj


# Access to the correct "Inspect" instance for this worker
_inspector = None


def _worker_inspector(task):
    global _inspector

    if _inspector is None:
        try:
            # Celery >= 5
            from ..app import app
            inspect = app.control.inspect
        except AttributeError:
            # Celecy < 5
            from celery.app.control import Inspect as inspect  # noqa: N813
        _inspector = inspect([task.request.hostname])

    return _inspector


# Get this list of currently revoked tasks for this worker
def _revoked_tasks(task):
    _revoked = _worker_inspector(task).revoked()

    if _revoked is None:
        return []

    return _revoked.get(task.request.hostname, [])


def deserialize_job_info_spec(**kwargs):
    return JobManager(**kwargs)


class JobSpecNotFound(Exception):
    pass


def _job_manager(request=None, headers=None, kwargs=None):

    girder_client_session_kwargs = {}
    if hasattr(request, 'girder_client_session_kwargs'):
        girder_client_session_kwargs = request.girder_client_session_kwargs

    if hasattr(request, 'jobInfoSpec'):
        jobSpec = request.jobInfoSpec

    # We are being called from revoked signal
    elif headers is not None and \
            'jobInfoSpec' in headers:
        jobSpec = headers['jobInfoSpec']

    # Deprecated: This method of passing job information
    # to girder_worker is deprecated. Newer versions of girder
    # pass this information automatically as apart of the
    # header metadata in the worker scheduler.
    elif kwargs and 'jobInfo' in kwargs:
        jobSpec = kwargs.pop('jobInfo', {})

    else:
        raise JobSpecNotFound

    override = resolve_girder_api_url()
    if override:
        original = None
        if request is not None:
            original = getattr(request, 'girder_api_url', None)
            if original is None:
                original = getattr(request, 'apiUrl', None)
        if original is None and headers is not None:
            original = headers.get('girder_api_url') or headers.get('apiUrl')
        jobSpec = dict(jobSpec)
        if 'url' in jobSpec:
            jobSpec['url'] = rewrite_url_api_base(
                jobSpec['url'], original, override)

    return deserialize_job_info_spec(
        **jobSpec, girder_client_session_kwargs=girder_client_session_kwargs)


def _update_status(task, status):
    task.job_manager.updateStatus(status)


def is_revoked(task):
    """
    Utility function to check if a task has been revoked.

    Eager tasks are never considered revoked.

    :param task: The task.
    :type task: celery.app.task.Task
    :return: True, if this task is in the revoked list for this worker, False
            otherwise.
    :rtype: bool
    """
    if task.request.is_eager:
        return False
    return task.request.id in _revoked_tasks(task)


def girder_job(title=None, type='celery', public=False,
               handler='celery_handler', otherFields=None):
    """Decorator that populates a girder_worker celery task with
    girder's job metadata.

    :param title: The title of the job in girder.
    :type title: str
    :param type: The type of the job in girder.
    :type type: str
    :param public: Public read access flag for girder.
    :type public: bool
    :param handler: If this job should be handled by a specific handler,
        'celery_handler' by default cannot be scheduled in girder.
    :param otherFields: Any additional fields to set on the job in girder.
    :type otherFields: dict
    """
    otherFields = otherFields or {}

    def _girder_job(task_obj):
        task_obj._girder_job_title = title
        task_obj._girder_job_type = type
        task_obj._girder_job_public = public
        task_obj._girder_job_handler = handler
        task_obj._girder_job_other_fields = otherFields
        return task_obj

    return _girder_job


class JobStatus:
    INACTIVE = 0
    QUEUED = 1
    RUNNING = 2
    SUCCESS = 3
    ERROR = 4
    CANCELED = 5

    FETCHING_INPUT = 820
    CONVERTING_INPUT = 821
    CONVERTING_OUTPUT = 822
    PUSHING_OUTPUT = 823
    CANCELING = 824


class StateTransitionException(Exception):
    pass


class TeeCustomWrite(Tee):
    def __init__(self, func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._write_func = func

    def write(self, *args, **kwargs):
        self._write_func(*args, **kwargs)
        super().write(*args, **kwargs)


@tee_stdout
class TeeStdOutCustomWrite(TeeCustomWrite):
    pass


@tee_stderr
class TeeStdErrCustomWrite(TeeCustomWrite):
    pass


class JobManager:
    """
    This class can be used to write log messages to Girder by capturing
    stdout/stderr printed within the context and sending them in a
    rate-limited manner to Girder. This is not threadsafe since it changes
    the global values of sys.stdout/sys.stderr.

    It also exposes utilities for updating other job fields such as progress
    and status.
    """

    def __init__(self, logPrint, url, method=None, headers=None, interval=0.5,
                 reference=None, girder_client_session_kwargs=None):
        """
        :param on: Whether print messages should be logged to the job log.
        :type on: bool
        :param url: The job update URL.
        :param method: The HTTP method to use when updating the job.
        :param headers: Optional HTTP header dict
        :param interval: Minimum time interval at which to send log updates
        back to Girder over HTTP (seconds).
        :type interval: int or float
        :param reference: optional reference to store with the job.
        """
        from ..app import CeleryAppInfo

        # When we are using a threads pool, tee-ing stdout and stderr to
        # logPrint can lead to the logs being written to multiple threads and
        # therefore multiple workers.
        if CeleryAppInfo['threads_pool']:
            logPrint = None
        self.logPrint = logPrint
        self.method = method or 'PUT'
        self.url = url
        self.headers = headers or {}
        self.interval = interval
        self.status = None
        self.reference = reference

        self._last = time.time()
        self._buf = b''
        self._progressTotal = None
        self._progressCurrent = None
        self._progressMessage = None

        self._session = requests.Session()
        retryAdapter = requests.adapters.HTTPAdapter(max_retries=10)
        self._session.mount('http://', retryAdapter)
        self._session.mount('https://', retryAdapter)

        if girder_client_session_kwargs:
            for attr, value in girder_client_session_kwargs.items():
                setattr(self._session, attr, value)

        if logPrint:
            self._stdout = TeeStdOutCustomWrite(self.write)
            self._stderr = TeeStdErrCustomWrite(self.write)

    def cleanup(self):
        self._session.close()
        if self.logPrint:
            self._stdout.reset()
            self._stderr.reset()

    def _flush(self):
        """
        If there are contents in the buffer, send them up to the server. If the
        buffer is empty, this is a no-op.
        """
        if not self.url:
            return

        if len(self._buf) or self._progressTotal or self._progressMessage or \
                self._progressCurrent is not None:
            data = {
                'progressTotal': self._progressTotal,
                'progressCurrent': self._progressCurrent,
                'progressMessage': self._progressMessage
            }
            if self._buf:
                data['log'] = self._buf

            req = self._session.request(
                self.method.upper(), self.url, allow_redirects=True,
                headers=self.headers, data=data)
            req.raise_for_status()
            self._buf = b''

    def write(self, message, forceFlush=False):
        """
        Append a message to the log for this job. If logPrint is enabled, this
        will be called whenever stdout or stderr is printed to. Otherwise it
        can be called manually and will still perform rate-limited flushing to
        the server.

        :param message: The message to append to the job log.
        :type message: str
        :param forceFlush: Whether to force the write of this event to the
            server. Useful if you don't expect another update for some time.
        :type forceFlush: bool
        """
        if isinstance(message, str):
            message = message.encode('utf8')

        self._buf += message

        if forceFlush or time.time() - self._last > self.interval:
            self._flush()
            self._last = time.time()

    def updateStatus(self, status):
        """
        Update the status field of a job.

        :param status: The status to set on the job.
        :type status: JobStatus
        """
        if not self.url or status is None or status == self.status:
            return

        # Ensure that the logs are flushed before the status is changed
        self._flush()
        self.status = status
        try:
            req = self._session.request(self.method.upper(), self.url, headers=self.headers,
                                        data={'status': status}, allow_redirects=True)
            req.raise_for_status()
        except HTTPError as hex:
            if hex.response.status_code == 400:
                json_response = hex.response.json()
                if 'field' in json_response and json_response['field'] == 'status':
                    print(json_response['message'])
                    raise StateTransitionException(json_response['message'], hex)
                else:
                    raise
            else:
                raise

    def updateProgress(self, total=None, current=None, message=None,
                       forceFlush=False):
        """
        Update the progress information about a job.

        :param total: The total progress value, or None to leave the same.
        :type total: int, float, or None
        :param current: The current progress value, or None to leave the same.
        :type current: int, float, or None
        :param message: Progress message to set, or None to leave the same.
        :type message: str or None
        :param forceFlush: Whether to force the write of this event to the
            server. Useful if you don't expect another update for some time.
        :type forceFlush: bool
        """
        if total is not None:
            self._progressTotal = total
        if current is not None:
            self._progressCurrent = current
        if message is not None:
            self._progressMessage = message

        if forceFlush or time.time() - self._last > self.interval:
            self._flush()
            self._last = time.time()

    def refreshStatus(self):
        """
        Refresh the status field from Girder
        """
        r = self._session.get(self.url, headers=self.headers, allow_redirects=True)
        self.status = r.json()['status']

        return self.status
