from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, filtermodel
from girder.utility.model_importer import ModelImporter

from common_tasks.test_tasks.fib import fibonacci
from common_tasks.test_tasks.cancel import cancelable
from common_tasks.test_tasks.fail import fail_after
from common_tasks.test_tasks.girder_client import request_private_path

import multiprocessing
from girder_worker.utils import JobStatus

from .utilities import wait_for_status


# N.B. Module is named raw to avoid conflict with celery package
class CeleryTestEndpoints(Resource):
    def __init__(self):
        super().__init__()
        self.route('POST', ('test_task_delay', ),
                   self.test_celery_task_delay)
        self.route('POST', ('test_task_delay_fails', ),
                   self.test_celery_task_delay_fails)
        self.route('POST', ('test_task_apply_async', ),
                   self.test_celery_task_apply_async)
        self.route('POST', ('test_task_apply_async_fails', ),
                   self.test_celery_task_apply_async_fails)
        self.route('POST', ('test_task_signature_delay', ),
                   self.test_celery_task_signature_delay)
        self.route('POST', ('test_task_signature_delay_fails', ),
                   self.test_celery_task_signature_delay_fails)
        self.route('POST', ('test_task_signature_apply_async', ),
                   self.test_celery_task_signature_apply_async)
        self.route('POST', ('test_task_signature_apply_async_fails', ),
                   self.test_celery_task_signature_apply_async_fails)
        self.route('POST', ('test_task_revoke', ),
                   self.test_celery_task_revoke)
        self.route('POST', ('test_task_revoke_in_queue', ),
                   self.test_celery_task_revoke_in_queue)
        self.route('POST', ('test_task_chained', ),
                   self.test_celery_task_chained)
        self.route('POST', ('test_task_chained_bad_token_fails', ),
                   self.test_celery_task_chained_bad_token_fails)

        self.route('POST', ('test_task_delay_with_custom_job_options', ),
                   self.test_celery_task_delay_with_custom_job_options)
        self.route('POST', ('test_task_apply_async_with_custom_job_options', ),
                   self.test_celery_task_apply_async_with_custom_job_options)

        self.route('POST', ('test_girder_client_generation', ),
                   self.test_celery_girder_client_generation)
        self.route('POST', ('test_girder_client_bad_token_fails', ),
                   self.test_celery_girder_client_bad_token_fails)
    # Testing custom job option API for celery tasks

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task delay with custom job options'))
    def test_celery_task_delay_with_custom_job_options(self, params):
        result = fibonacci.delay(20, girder_job_title='TEST DELAY TITLE')
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task apply_async with custom job options'))
    def test_celery_task_apply_async_with_custom_job_options(self, params):
        result = fibonacci.apply_async((20,), {}, girder_job_title='TEST APPLY_ASYNC TITLE')
        return result.job

    # Testing basic celery API

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task delay'))
    def test_celery_task_delay(self, params):
        result = fibonacci.delay(20)
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task delay fails correctly'))
    def test_celery_task_delay_fails(self, params):
        result = fail_after.delay()
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task apply_async'))
    def test_celery_task_apply_async(self, params):
        result = fibonacci.apply_async((20,))
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task apply_async fails correctly'))
    def test_celery_task_apply_async_fails(self, params):
        result = fail_after.apply_async((0.5,))
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task signature delay'))
    def test_celery_task_signature_delay(self, params):
        signature = fibonacci.s(20)
        result = signature.delay()
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task signature delay fails correctly'))
    def test_celery_task_signature_delay_fails(self, params):
        signature = fail_after.s(0.5)
        result = signature.delay()
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task apply_async'))
    def test_celery_task_signature_apply_async(self, params):
        signature = fibonacci.s(20)
        result = signature.apply_async()
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task apply_async fails correctly'))
    def test_celery_task_signature_apply_async_fails(self, params):
        signature = fail_after.s(0.5)
        result = signature.apply_async()
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test girder client is generated and can request scoped endpoints'))
    def test_celery_girder_client_generation(self, params):
        token = ModelImporter.model('token').createToken(
            user=self.getCurrentUser())

        result = request_private_path.delay(
            'admin', girder_client_token=str(token['_id']))

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description("Test girder client with no token can't access protected resources"))
    def test_celery_girder_client_bad_token_fails(self, params):
        result = request_private_path.delay('admin', girder_client_token='')

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test revoking a task directly'))
    def test_celery_task_revoke(self, params):
        result = cancelable.delay()
        # Make sure we are running before we revoke
        assert wait_for_status(self.getCurrentUser(), result.job, JobStatus.RUNNING)
        result.revoke()

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test revoking a task directly when in queue'))
    def test_celery_task_revoke_in_queue(self, params):
        # Fill up queue
        blockers = []
        for _ in range(0, multiprocessing.cpu_count()):
            blockers .append(cancelable.delay(sleep_interval=0.1))

        result = cancelable.delay()
        result.revoke()

        assert wait_for_status(self.getCurrentUser(), result.job, JobStatus.CANCELED)

        # Now clean up the blockers
        for blocker in blockers:
            blocker.revoke()

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test chained celery tasks')
    )
    def test_celery_task_chained(self, params):
        jobModel = ModelImporter.model('job', 'jobs')
        user = self.getCurrentUser()
        # F(F(F(6))) --> F(F(8)) --> F(21) --> 10946
        result = (fibonacci.s(6) | fibonacci.s() | fibonacci.s()).delay()
        result.wait(timeout=10)
        job_1 = result.job
        job_2 = jobModel.load(job_1['parentId'], user=user)
        job_3 = jobModel.load(job_2['parentId'], user=user)

        return [job_1, job_2, job_3]

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test chained celery tasks with a bad token')
    )
    def test_celery_task_chained_bad_token_fails(self, params):
        jobModel = ModelImporter.model('job', 'jobs')
        result = (fibonacci.s(5)
                  | request_private_path.si('admin', girder_client_token='')).delay()

        # Bypass the raised exception from the second job
        try:
            result.wait(timeout=10)
        except Exception:
            pass

        user = self.getCurrentUser()
        job_1 = result.job
        job_2 = jobModel.load(job_1['parentId'], user=user)
        return [job_1, job_2]
