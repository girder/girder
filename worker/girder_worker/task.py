import celery
from celery.result import AsyncResult

from girder_worker.context import get_context
from girder_worker.utils import is_builtin_celery_task, is_revoked, _walk_obj
from girder_worker.utils.decorators import describe_function


class GirderAsyncResult(AsyncResult):
    def __init__(self, *args, **kwargs):
        self._job = None
        super().__init__(*args, **kwargs)

    @property
    def job(self):
        context = get_context()
        if self._job is None:
            self._job = context.get_async_result_job_property(self)
        return self._job


class Task(celery.Task):
    """
    Girder Worker Task object. Tasks defined by plugins must be subclasses of this class,
    however you will typically not need to reference it yourself, as it will be automatically
    instantiated by the girder_worker celery app. See :ref:`creating-tasks` for instructions.
    """

    _girder_job_title = '<unnamed job>'
    _girder_job_type = 'celery'
    _girder_job_public = False
    _girder_job_handler = 'celery_handler'
    _girder_job_other_fields = {}

    @classmethod
    def girder_job_defaults(cls):
        return {
            'girder_job_title': cls._girder_job_title,
            'girder_job_type': cls._girder_job_type,
            'girder_job_public': cls._girder_job_public,
            'girder_job_handler': cls._girder_job_handler,
            'girder_job_other_fields': cls._girder_job_other_fields
        }

    # These keys will be removed from apply_async's kwargs or options and
    # transfered into the headers of the message.
    reserved_headers = [
        'girder_client_token',
        'girder_api_url',
        'girder_result_hooks',
        'girder_client_session_kwargs']

    # These keys will be available in the 'properties' dictionary inside
    # girder_before_task_publish() but will not be passed along in the message
    reserved_options = [
        'girder_user',
        'girder_job_title',
        'girder_job_type',
        'girder_job_public',
        'girder_job_handler',
        'girder_job_other_fields']

    def AsyncResult(self, task_id, **kwargs):
        return GirderAsyncResult(task_id, backend=self.backend,
                                 task_name=self.name, app=self.app, **kwargs)

    def apply_async(self, args=None, kwargs=None, task_id=None, producer=None,
                    link=None, link_error=None, shadow=None, **options):

        if is_builtin_celery_task(self.name):
            return super().apply_async(
                args=args, kwargs=kwargs, task_id=task_id, producer=producer,
                link=link, link_error=link_error, shadow=shadow, **options)

        # Pass girder related job information through to
        # the signals by adding this information to options['headers']
        # This sets defaults for reserved_options based on the class defaults,
        # or values defined by the girder_job() dectorator
        headers = {
            'girder_job_title': self._girder_job_title,
            'girder_job_type': self._girder_job_type,
            'girder_job_public': self._girder_job_public,
            'girder_job_handler': self._girder_job_handler,
            'girder_job_other_fields': self._girder_job_other_fields,
        }

        # Certain keys may show up in either kwargs (e.g. via
        # .delay(girder_token='foo') or in options (e.g.
        # .apply_async(args=(), kwargs={}, girder_token='foo') For
        # those special headers, pop them out of kwargs or options and
        # put them in headers so they can be picked up by the
        # before_task_publish signal.
        for key in self.reserved_headers + self.reserved_options:
            if kwargs is not None and key in kwargs:
                headers[key] = kwargs.pop(key)
            if key in options:
                headers[key] = options.pop(key)

        if 'headers' in options:
            if options['headers'] is None:
                options['headers'] = headers
            else:
                options['headers'].update(headers)
        else:
            options['headers'] = headers

        return super().apply_async(
            args=args, kwargs=kwargs, task_id=task_id, producer=producer,
            link=link, link_error=link_error, shadow=shadow, serializer='girder_io', **options)

    @property
    def canceled(self):
        """
        A property to indicate if a task has been canceled.

        :return: True is this task has been canceled, False otherwise.
        :rtype: bool
        """
        return is_revoked(self)

    def describe(self):
        return describe_function(self.run)

    def call_item_task(self, inputs, outputs=None):
        if outputs is None:
            outputs = {}
        return self.run.call_item_task(inputs, outputs)

    def _maybe_transform_result(self, idx, result, **kwargs):
        try:
            grh = self.request.girder_result_hooks[idx]
            if hasattr(grh, 'transform') and callable(grh.transform):
                return grh.transform(result, **kwargs)
            return result
        except IndexError:
            return result

    def _maybe_transform_argument(self, arg, **kwargs):
        if hasattr(arg, 'transform') and callable(arg.transform):
            return arg.transform(**kwargs)
        return arg

    def _maybe_cleanup(self, arg, **kwargs):
        if hasattr(arg, 'cleanup') and callable(arg.cleanup):
            arg.cleanup(**kwargs)

    def __call__(self, *args, **kwargs):
        try:
            _t_args = _walk_obj(args, self._maybe_transform_argument)
            _t_kwargs = _walk_obj(kwargs, self._maybe_transform_argument)

            results = super().__call__(*_t_args, **_t_kwargs)

            if hasattr(self.request, 'girder_result_hooks'):
                if isinstance(results, tuple):
                    results = tuple([self._maybe_transform_result(i, r)
                                     for i, r in enumerate(results)])
                else:
                    results = self._maybe_transform_result(0, results)

            return results
        except Exception:
            if hasattr(self.request, 'girder_result_hooks'):
                for hook in self.request.girder_result_hooks:
                    hook.exception()
            raise
        finally:
            _walk_obj(args, self._maybe_cleanup)
            _walk_obj(kwargs, self._maybe_cleanup)
            if hasattr(self.request, 'girder_result_hooks'):
                for hook in self.request.girder_result_hooks:
                    self._maybe_cleanup(hook)
