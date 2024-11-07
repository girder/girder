import warnings
import functools
import contextlib
from girder_worker.utils import JobStatus
import time
from requests_toolbelt.sessions import BaseUrlSession
from datetime import timedelta, datetime


class GirderSession(BaseUrlSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.wait_for_success = functools.partial(
            self.wait_for,
            predicate=lambda j:
                j['status'] == JobStatus.SUCCESS,
            on_timeout=lambda j:
                'Timed out waiting for job/%s to move into success state' % j['_id'])

        self.wait_for_error = functools.partial(
            self.wait_for,
            predicate=lambda j:
                j['status'] == JobStatus.ERROR,
            on_timeout=lambda j:
                'Timed out waiting for job/%s to move into error state' % j['_id'])

        self.wait_for_canceled = functools.partial(
            self.wait_for,
            predicate=lambda j:
                j['status'] == JobStatus.CANCELED,
            on_timeout=lambda j:
                'Timed out waiting for job/%s to move into canceled state' % j['_id'])

    def get_result(self, celery_id):
        r = self.post('integration_tests/common/result', data={
            'celery_id': celery_id})
        return r.text

    @contextlib.contextmanager
    def wait_for(self, job_id, predicate, timeout=20, interval=0.3, on_timeout=None):
        """A generic context manager that handles waiting on properties of a job.

        :param job_id: ID of the job to wait on
        :param predicate: function that takes the job JSON and returns a boolean.
                          Return true to break out of the loop.
        :param timeout: Timeout after a fixed number of seconds
        :param interval: How often to check the job's status
        :param on_timeout: What to do if the function times out.
        :returns: (on success) yield's the job's JSON as a dict
        :rtype: dict

        """
        then = datetime.utcnow() + timedelta(seconds=timeout)
        timeout = True

        while datetime.utcnow() < then:
            r = self.get('job/' + job_id)
            r.raise_for_status()

            if predicate(r.json()):
                timeout = False
                break

            time.sleep(interval)

        r = self.get('job/' + job_id)

        if timeout:
            if on_timeout is None:
                def on_timeout(j):
                    return 'Timed out waiting for %s' % 'job/%s' % j['_id']

            warnings.warn(on_timeout(r.json()))

        yield r.json()
