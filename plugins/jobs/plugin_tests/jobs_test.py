# -*- coding: utf-8 -*-
import json
import time
from bson import json_util

from tests import base
from girder import events
from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.user import User
from girder.models.token import Token

from girder_jobs.constants import JobStatus, REST_CREATE_JOB_TOKEN_SCOPE
from girder_jobs.models.job import Job


def setUpModule():
    base.enabledPlugins.append('jobs')
    base.startServer()


def tearDownModule():
    base.stopServer()


class JobsTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        self.users = [User().createUser(
            'usr' + str(n), 'passwd', 'tst', 'usr', 'u%d@u.com' % n)
            for n in range(3)]

        self.jobModel = Job()

    def testJobs(self):
        self.job = None

        def schedule(event):
            self.job = event.info
            if self.job['handler'] == 'my_handler':
                self.job['status'] = JobStatus.RUNNING
                self.job = self.jobModel.save(self.job)
                self.assertEqual(self.job['args'], ('hello', 'world'))
                self.assertEqual(self.job['kwargs'], {'a': 'b'})

        events.bind('jobs.schedule', 'test', schedule)

        # Create a job
        job = self.jobModel.createJob(
            title='Job Title', type='my_type', args=('hello', 'world'),
            kwargs={'a': 'b'}, user=self.users[1], handler='my_handler',
            public=False)
        self.assertEqual(self.job, None)
        self.assertEqual(job['status'], JobStatus.INACTIVE)

        # Schedule the job, make sure our handler was invoked
        self.jobModel.scheduleJob(job)
        self.assertEqual(self.job['_id'], job['_id'])
        self.assertEqual(self.job['status'], JobStatus.RUNNING)

        # Since the job is not public, user 2 should not have access
        path = '/job/%s' % job['_id']
        resp = self.request(path, user=self.users[2])
        self.assertStatus(resp, 403)
        resp = self.request(path, user=self.users[2], method='PUT')
        self.assertStatus(resp, 403)
        resp = self.request(path, user=self.users[2], method='DELETE')
        self.assertStatus(resp, 403)

        # If no user is specified, we should get a 401 error
        resp = self.request(path, user=None)
        self.assertStatus(resp, 401)

        # Make sure user who created the job can see it
        resp = self.request(path, user=self.users[1])
        self.assertStatusOk(resp)

        # We should be able to update the job as the user who created it
        resp = self.request(path, method='PUT', user=self.users[1], params={
            'log': 'My log message\n'
        })
        self.assertStatusOk(resp)

        # We should be able to create a job token and use that to update it too
        token = self.jobModel.createJobToken(job)
        resp = self.request(path, method='PUT', params={
            'log': 'append message',
            'token': token['_id']
        })
        self.assertStatusOk(resp)
        # We shouldn't get the log back in this case
        self.assertNotIn('log', resp.json)

        # Do a fetch on the job itself to get the log
        resp = self.request(path, user=self.users[1])
        self.assertStatusOk(resp)
        self.assertEqual(
            resp.json['log'], ['My log message\n', 'append message'])

        # Test overwriting the log and updating status
        resp = self.request(path, method='PUT', params={
            'log': 'overwritten log',
            'overwrite': 'true',
            'status': JobStatus.SUCCESS,
            'token': token['_id']
        })
        self.assertStatusOk(resp)
        self.assertNotIn('log', resp.json)
        self.assertEqual(resp.json['status'], JobStatus.SUCCESS)

        job = self.jobModel.load(job['_id'], force=True, includeLog=True)
        self.assertEqual(job['log'], ['overwritten log'])

        # We should be able to delete the job as the user who created it
        resp = self.request(path, user=self.users[1], method='DELETE')
        self.assertStatusOk(resp)
        job = self.jobModel.load(job['_id'], force=True)
        self.assertIsNone(job)

    def testLegacyLogBehavior(self):
        # Force save a job with a string log to simulate a legacy job record
        job = self.jobModel.createJob(
            title='legacy', type='legacy', user=self.users[1], save=False)
        job['log'] = 'legacy log'
        job = self.jobModel.save(job, validate=False)

        self.assertEqual(job['log'], 'legacy log')

        # Load the record, we should now get the log as a list
        job = self.jobModel.load(job['_id'], force=True, includeLog=True)
        self.assertEqual(job['log'], ['legacy log'])

    def testListJobs(self):
        job = self.jobModel.createJob(title='A job', type='t', user=self.users[1], public=False)
        anonJob = self.jobModel.createJob(title='Anon job', type='t')
        # Ensure timestamp for public job is strictly higher (ms resolution)
        time.sleep(0.1)
        publicJob = self.jobModel.createJob(
            title='Anon job', type='t', public=True)

        # User 1 should be able to see their own jobs
        resp = self.request('/job', user=self.users[1], params={
            'userId': self.users[1]['_id']
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], str(job['_id']))

        # User 2 should not see user 1's jobs in the list
        resp = self.request('/job', user=self.users[2], params={
            'userId': self.users[1]['_id']
        })
        self.assertEqual(resp.json, [])

        # Omitting a userId should assume current user
        resp = self.request('/job', user=self.users[1])
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], str(job['_id']))

        # Explicitly passing "None" should show anonymous jobs
        resp = self.request('/job', user=self.users[0], params={
            'userId': 'none'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[0]['_id'], str(publicJob['_id']))
        self.assertEqual(resp.json[1]['_id'], str(anonJob['_id']))

        # Non-admins should only see public anon jobs
        resp = self.request('/job', params={'userId': 'none'})
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], str(publicJob['_id']))

    def testListAllJobs(self):
        self.jobModel.createJob(title='user 0 job', type='t', user=self.users[0], public=False)
        self.jobModel.createJob(title='user 1 job', type='t', user=self.users[1], public=False)
        self.jobModel.createJob(title='user 1 job', type='t', user=self.users[1], public=True)
        self.jobModel.createJob(title='user 2 job', type='t', user=self.users[2])
        self.jobModel.createJob(title='anonymous job', type='t')
        self.jobModel.createJob(title='anonymous public job', type='t2', public=True)

        # User 0, as a site admin, should be able to see all jobs
        resp = self.request('/job/all', user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 6)

        # get with filter
        resp = self.request('/job/all', user=self.users[0], params={
            'types': json.dumps(['t']),
            'statuses': json.dumps([0])
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 5)

        # get with unmet filter conditions
        resp = self.request('/job/all', user=self.users[0], params={
            'types': json.dumps(['nonexisttype'])
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 0)

        # User 1, as non site admin, should encounter http 403 (Forbidden)
        resp = self.request('/job/all', user=self.users[1])
        self.assertStatus(resp, 403)

        # Not authenticated user should encounter http 401 (unauthorized)
        resp = self.request('/job/all')
        self.assertStatus(resp, 401)

    def testFiltering(self):
        job = self.jobModel.createJob(title='A job', type='t', user=self.users[1], public=True)

        job['_some_other_field'] = 'foo'
        job = self.jobModel.save(job)

        resp = self.request('/job/%s' % job['_id'])
        self.assertStatusOk(resp)
        self.assertTrue('created' in resp.json)
        self.assertTrue('_some_other_field' not in resp.json)
        self.assertTrue('kwargs' not in resp.json)
        self.assertTrue('args' not in resp.json)

        resp = self.request('/job/%s' % job['_id'], user=self.users[0])
        self.assertTrue('kwargs' in resp.json)
        self.assertTrue('args' in resp.json)

        self.jobModel.exposeFields(level=AccessType.READ, fields={'_some_other_field'})
        self.jobModel.hideFields(level=AccessType.READ, fields={'created'})

        resp = self.request('/job/%s' % job['_id'])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['_some_other_field'], 'foo')
        self.assertTrue('created' not in resp.json)

    def testJobProgressAndNotifications(self):
        job = self.jobModel.createJob(title='a job', type='t', user=self.users[1], public=True)

        path = '/job/%s' % job['_id']
        resp = self.request(path)
        self.assertEqual(resp.json['progress'], None)
        self.assertEqual(resp.json['timestamps'], [])

        resp = self.request(path, method='PUT', user=self.users[1], params={
            'progressTotal': 100,
            'progressCurrent': 3,
            'progressMessage': 'Started',
            'notify': 'false',
            'status': JobStatus.QUEUED
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['progress'], {
            'total': 100,
            'current': 3,
            'message': 'Started',
            'notificationId': None
        })

        # The status update should make it so we now have a timestamp
        self.assertEqual(len(resp.json['timestamps']), 1)
        self.assertEqual(resp.json['timestamps'][0]['status'], JobStatus.QUEUED)
        self.assertIn('time', resp.json['timestamps'][0])

        # If the status does not change on update, no timestamp should be added
        resp = self.request(path, method='PUT', user=self.users[1], params={
            'status': JobStatus.QUEUED
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['timestamps']), 1)
        self.assertEqual(resp.json['timestamps'][0]['status'], JobStatus.QUEUED)

        # We passed notify=false, so we should only have the job creation notification
        resp = self.request(path='/notification/stream', method='GET',
                            user=self.users[1], isJson=False,
                            params={'timeout': 0})
        messages = self.getSseMessages(resp)
        self.assertEqual(len(messages), 1)

        # Update progress with notify=true (the default)
        resp = self.request(path, method='PUT', user=self.users[1], params={
            'progressCurrent': 50,
            'progressMessage': 'Something bad happened',
            'status': JobStatus.ERROR
        })
        self.assertStatusOk(resp)
        self.assertNotEqual(resp.json['progress']['notificationId'], None)

        # We should now see three notifications (job created + job status + progress)
        resp = self.request(path='/notification/stream', method='GET',
                            user=self.users[1], isJson=False,
                            params={'timeout': 0})
        messages = self.getSseMessages(resp)
        job = self.jobModel.load(job['_id'], force=True)
        self.assertEqual(len(messages), 3)
        creationNotify = messages[0]
        progressNotify = messages[1]
        statusNotify = messages[2]

        self.assertEqual(creationNotify['type'], 'job_created')
        self.assertEqual(creationNotify['data']['_id'], str(job['_id']))
        self.assertEqual(statusNotify['type'], 'job_status')
        self.assertEqual(statusNotify['data']['_id'], str(job['_id']))
        self.assertEqual(int(statusNotify['data']['status']), JobStatus.ERROR)
        self.assertNotIn('kwargs', statusNotify['data'])
        self.assertNotIn('log', statusNotify['data'])

        self.assertEqual(progressNotify['type'], 'progress')
        self.assertEqual(progressNotify['data']['title'], job['title'])
        self.assertEqual(progressNotify['data']['current'], float(50))
        self.assertEqual(progressNotify['data']['state'], 'error')
        self.assertEqual(progressNotify['_id'], str(job['progress']['notificationId']))

    def testDotsInKwargs(self):
        kwargs = {
            '$key.with.dots': 'value',
            'foo': [{
                'moar.dots': True
            }]
        }
        job = self.jobModel.createJob(title='dots', type='x', user=self.users[0], kwargs=kwargs)

        # Make sure we can update a job and notification creation works
        self.jobModel.updateJob(job, status=JobStatus.QUEUED, notify=True)

        self.assertEqual(job['kwargs'], kwargs)

        resp = self.request('/job/%s' % job['_id'], user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['kwargs'], kwargs)

        job = self.jobModel.load(job['_id'], force=True)
        self.assertEqual(job['kwargs'], kwargs)
        job = self.jobModel.filter(job, self.users[0])
        self.assertEqual(job['kwargs'], kwargs)
        job = self.jobModel.filter(job, self.users[1])
        self.assertFalse('kwargs' in job)

    def testLocalJob(self):
        job = self.jobModel.createLocalJob(
            title='local', type='local', user=self.users[0], kwargs={
                'hello': 'world'
            }, module='plugin_tests.local_job_impl')

        self.jobModel.scheduleJob(job)

        job = self.jobModel.load(job['_id'], force=True, includeLog=True)
        self.assertEqual(job['log'], ['job ran!'])

        job = self.jobModel.createLocalJob(
            title='local', type='local', user=self.users[0], kwargs={
                'hello': 'world'
            }, module='plugin_tests.local_job_impl', function='fail')

        self.jobModel.scheduleJob(job)

        job = self.jobModel.load(job['_id'], force=True, includeLog=True)
        self.assertEqual(job['log'], ['job failed'])

    def testValidateCustomStatus(self):
        job = self.jobModel.createJob(title='test', type='x', user=self.users[0])

        def validateStatus(event):
            if event.info == 1234:
                event.preventDefault().addResponse(True)

        def validTransitions(event):
            if event.info['status'] == 1234:
                event.preventDefault().addResponse([JobStatus.INACTIVE])

        with self.assertRaises(ValidationException):
            self.jobModel.updateJob(job, status=1234)  # Should fail

        with events.bound('jobs.status.validate', 'test', validateStatus), \
                events.bound('jobs.status.validTransitions', 'test', validTransitions):
            self.jobModel.updateJob(job, status=1234)  # Should work

            with self.assertRaises(ValidationException):
                self.jobModel.updateJob(job, status=4321)  # Should fail

    def testValidateCustomStrStatus(self):
        job = self.jobModel.createJob(title='test', type='x', user=self.users[0])

        def validateStatus(event):
            states = ['a', 'b', 'c']

            if event.info in states:
                event.preventDefault().addResponse(True)

        def validTransitions(event):
            if event.info['status'] == 'a':
                event.preventDefault().addResponse([JobStatus.INACTIVE])

        with self.assertRaises(ValidationException):
            self.jobModel.updateJob(job, status='a')

        with events.bound('jobs.status.validate', 'test', validateStatus), \
                events.bound('jobs.status.validTransitions', 'test', validTransitions):
            self.jobModel.updateJob(job, status='a')
            self.assertEqual(job['status'], 'a')

        with self.assertRaises(ValidationException), \
                events.bound('jobs.status.validate', 'test', validateStatus):
            self.jobModel.updateJob(job, status='foo')

    def testUpdateOtherFields(self):
        job = self.jobModel.createJob(title='test', type='x', user=self.users[0])
        job = self.jobModel.updateJob(job, otherFields={'other': 'fields'})
        self.assertEqual(job['other'], 'fields')

    def testCancelJob(self):
        job = self.jobModel.createJob(title='test', type='x', user=self.users[0])
        # add to the log
        job = self.jobModel.updateJob(job, log='entry 1\n')
        # Reload without the log
        job = self.jobModel.load(id=job['_id'], force=True)
        self.assertEqual(len(job.get('log', [])), 0)
        # Cancel
        job = self.jobModel.cancelJob(job)
        self.assertEqual(job['status'], JobStatus.CANCELED)
        # Reloading should still have the log and be canceled
        job = self.jobModel.load(id=job['_id'], force=True, includeLog=True)
        self.assertEqual(job['status'], JobStatus.CANCELED)
        self.assertEqual(len(job.get('log', [])), 1)

    def testCancelJobEndpoint(self):
        job = self.jobModel.createJob(title='test', type='x', user=self.users[0])

        # Ensure requires write perms
        jobCancelUrl = '/job/%s/cancel' % job['_id']
        resp = self.request(jobCancelUrl, user=self.users[1], method='PUT')
        self.assertStatus(resp, 403)

        # Try again with the right user
        jobCancelUrl = '/job/%s/cancel' % job['_id']
        resp = self.request(jobCancelUrl, user=self.users[0], method='PUT')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['status'], JobStatus.CANCELED)

    def testJobsTypesAndStatuses(self):
        self.jobModel.createJob(title='user 0 job', type='t1', user=self.users[0], public=False)
        self.jobModel.createJob(title='user 1 job', type='t2', user=self.users[1], public=False)
        self.jobModel.createJob(title='user 1 job', type='t3', user=self.users[1], public=True)
        self.jobModel.createJob(title='user 2 job', type='t4', user=self.users[2])
        self.jobModel.createJob(title='anonymous job', type='t5')
        self.jobModel.createJob(title='anonymous public job', type='t6', public=True)

        # User 1, as non site admin, should encounter http 403 (Forbidden)
        resp = self.request('/job/typeandstatus/all', user=self.users[1])
        self.assertStatus(resp, 403)

        # Admin user gets all types and statuses
        resp = self.request('/job/typeandstatus/all', user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['types']), 6)
        self.assertEqual(len(resp.json['statuses']), 1)

        # standard user gets types and statuses of its own jobs
        resp = self.request('/job/typeandstatus', user=self.users[1])
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['types']), 2)
        self.assertEqual(len(resp.json['statuses']), 1)

    def testDefaultParentId(self):
        job = self.jobModel.createJob(title='Job', type='Job', user=self.users[0])
        # If not specified parentId should be None
        self.assertEquals(job['parentId'], None)

    def testIsParentIdCorrect(self):
        parentJob = self.jobModel.createJob(
            title='Parent Job', type='Parent Job', user=self.users[0])

        childJob = self.jobModel.createJob(
            title='Child Job', type='Child Job', user=self.users[0], parentJob=parentJob)
        # During initialization parent job should be set correctly
        self.assertEqual(childJob['parentId'], parentJob['_id'])

    def testSetParentCorrectly(self):
        parentJob = self.jobModel.createJob(
            title='Parent Job', type='Parent Job', user=self.users[0])
        childJob = self.jobModel.createJob(title='Child Job', type='Child Job', user=self.users[0])

        self.jobModel.setParentJob(childJob, parentJob)

        # After setParentJob method is called parent job should be set correctly
        self.assertEqual(childJob['parentId'], parentJob['_id'])

    def testParentCannotBeEqualToChild(self):
        childJob = self.jobModel.createJob(title='Child Job', type='Child Job', user=self.users[0])

        # Cannot set a job as it's own parent
        with self.assertRaises(ValidationException):
            self.jobModel.setParentJob(childJob, childJob)

    def testParentIdCannotBeOverridden(self):
        parentJob = self.jobModel.createJob(
            title='Parent Job', type='Parent Job', user=self.users[0])

        anotherParentJob = self.jobModel.createJob(
            title='Another Parent Job', type='Parent Job', user=self.users[0])

        childJob = self.jobModel.createJob(
            title='Child Job', type='Child Job', user=self.users[0], parentJob=parentJob)

        with self.assertRaises(ValidationException):
            # If parent job is set, cannot be overridden
            self.jobModel.setParentJob(childJob, anotherParentJob)

    def testListChildJobs(self):
        parentJob = self.jobModel.createJob(
            title='Parent Job', type='Parent Job', user=self.users[0])

        childJob = self.jobModel.createJob(
            title='Child Job', type='Child Job', user=self.users[0], parentJob=parentJob)

        self.jobModel.createJob(
            title='Another Child Job', type='Child Job', user=self.users[0], parentJob=parentJob)

        # Should return a list with 2 jobs
        self.assertEquals(len(list(self.jobModel.listChildJobs(parentJob))), 2)
        # Should return an empty list
        self.assertEquals(len(list(self.jobModel.listChildJobs(childJob))), 0)

    def testListChildJobsRest(self):
        parentJob = self.jobModel.createJob(
            title='Parent Job', type='Parent Job', user=self.users[0])

        childJob = self.jobModel.createJob(
            title='Child Job', type='Child Job', user=self.users[0], parentJob=parentJob)

        self.jobModel.createJob(
            title='Another Child Job', type='Child Job', user=self.users[0], parentJob=parentJob)

        resp = self.request('/job', user=self.users[0],
                            params={'parentId': str(parentJob['_id'])})
        resp2 = self.request('/job', user=self.users[0],
                             params={'parentId': str(childJob['_id'])})

        self.assertStatusOk(resp)
        self.assertStatusOk(resp2)

        # Should return a list with 2 jobs
        self.assertEquals(len(resp.json), 2)
        # Should return an empty list
        self.assertEquals(len(resp2.json), 0)

    def testCreateJobRest(self):
        resp = self.request('/job', method='POST',
                            user=self.users[0],
                            params={'title': 'job', 'type': 'job'})
        # If user does not have the necessary token status is 403
        self.assertStatus(resp, 403)

        token = Token().createToken(scope=REST_CREATE_JOB_TOKEN_SCOPE)

        resp2 = self.request(
            '/job', method='POST', token=token, params={'title': 'job', 'type': 'job'})
        # If user has the necessary token status is 200
        self.assertStatusOk(resp2)

    def testJobStateTransitions(self):
        job = self.jobModel.createJob(
            title='user 0 job', type='t1', user=self.users[0], public=False)

        # We can't move straight to SUCCESS
        with self.assertRaises(ValidationException):
            job = self.jobModel.updateJob(job, status=JobStatus.SUCCESS)

        self.jobModel.updateJob(job, status=JobStatus.QUEUED)
        self.jobModel.updateJob(job, status=JobStatus.RUNNING)
        self.jobModel.updateJob(job, status=JobStatus.ERROR)

        # We shouldn't be able to move backwards
        with self.assertRaises(ValidationException):
            self.jobModel.updateJob(job, status=JobStatus.QUEUED)
        with self.assertRaises(ValidationException):
            self.jobModel.updateJob(job, status=JobStatus.RUNNING)
        with self.assertRaises(ValidationException):
            self.jobModel.updateJob(job, status=JobStatus.INACTIVE)

    def testJobSaveEventModification(self):
        def customSave(event):
            kwargs = json_util.loads(event.info['kwargs'])
            kwargs['key2'] = 'newvalue'
            event.info['kwargs'] = json_util.dumps(kwargs)

        job = self.jobModel.createJob(title='A job', type='t', user=self.users[1], public=True)

        job['kwargs'] = {'key1': 'value1', 'key2': 'value2'}
        with events.bound('model.job.save', 'test', customSave):
            job = self.jobModel.save(job)
            self.assertEqual(job['kwargs']['key2'], 'newvalue')
