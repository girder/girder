#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import time

from tests import base
from girder import events
from girder.models.model_base import ValidationException


JobStatus = None


def setUpModule():
    base.enabledPlugins.append('jobs')
    base.startServer()

    global JobStatus
    from girder.plugins.jobs.constants import JobStatus


def tearDownModule():
    base.stopServer()


class JobsTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        self.users = [self.model('user').createUser(
            'usr' + str(n), 'passwd', 'tst', 'usr', 'u%d@u.com' % n)
            for n in range(3)]

    def testJobs(self):
        self.job = None

        def schedule(event):
            self.job = event.info
            if self.job['handler'] == 'my_handler':
                self.job['status'] = JobStatus.RUNNING
                self.model('job', 'jobs').save(self.job)
                self.assertEqual(self.job['args'], ('hello', 'world'))
                self.assertEqual(self.job['kwargs'], {'a': 'b'})

        events.bind('jobs.schedule', 'test', schedule)

        # Create a job
        job = self.model('job', 'jobs').createJob(
            title='Job Title', type='my_type', args=('hello', 'world'),
            kwargs={'a': 'b'}, user=self.users[1], handler='my_handler',
            public=False)
        self.assertEqual(self.job, None)
        self.assertEqual(job['status'], JobStatus.INACTIVE)

        # Schedule the job, make sure our handler was invoked
        self.model('job', 'jobs').scheduleJob(job)
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

        # Make sure user who created the job can see it
        resp = self.request(path, user=self.users[1])
        self.assertStatusOk(resp)

        # We should be able to update the job as the user who created it
        resp = self.request(path, method='PUT', user=self.users[1], params={
            'log': 'My log message\n'
        })
        self.assertStatusOk(resp)

        # We should be able to create a job token and use that to update it too
        token = self.model('job', 'jobs').createJobToken(job)
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

        job = self.model('job', 'jobs').load(
            job['_id'], force=True, includeLog=True)
        self.assertEqual(job['log'], ['overwritten log'])

        # We should be able to delete the job as the user who created it
        resp = self.request(path, user=self.users[1], method='DELETE')
        self.assertStatusOk(resp)
        job = self.model('job', 'jobs').load(job['_id'], force=True)
        self.assertIsNone(job)

    def testLegacyLogBehavior(self):
        # Force save a job with a string log to simulate a legacy job record
        job = self.model('job', 'jobs').createJob(
            title='legacy', type='legacy', user=self.users[1], save=False)
        job['log'] = 'legacy log'
        job = self.model('job', 'jobs').save(job, validate=False)

        self.assertEqual(job['log'], 'legacy log')

        # Load the record, we should now get the log as a list
        job = self.model('job', 'jobs').load(job['_id'], force=True,
                                             includeLog=True)
        self.assertEqual(job['log'], ['legacy log'])

    def testListJobs(self):
        job = self.model('job', 'jobs').createJob(
            title='A job', type='t', user=self.users[1], public=False)

        anonJob = self.model('job', 'jobs').createJob(
            title='Anon job', type='t')
        # Ensure timestamp for public job is strictly higher (ms resolution)
        time.sleep(0.1)
        publicJob = self.model('job', 'jobs').createJob(
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

    def testFiltering(self):
        job = self.model('job', 'jobs').createJob(
            title='A job', type='t', user=self.users[1], public=True)

        job['_some_other_field'] = 'foo'
        job = self.model('job', 'jobs').save(job)

        resp = self.request('/job/%s' % job['_id'])
        self.assertStatusOk(resp)
        self.assertTrue('created' in resp.json)
        self.assertTrue('_some_other_field' not in resp.json)
        self.assertTrue('kwargs' not in resp.json)
        self.assertTrue('args' not in resp.json)

        resp = self.request('/job/%s' % job['_id'], user=self.users[0])
        self.assertTrue('kwargs' in resp.json)
        self.assertTrue('args' in resp.json)

        def filterJob(event):
            event.info['job']['_some_other_field'] = 'bar'
            event.addResponse({
                'exposeFields': ['_some_other_field'],
                'removeFields': ['created']
            })

        events.bind('jobs.filter', 'test', filterJob)

        resp = self.request('/job/%s' % job['_id'])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['_some_other_field'], 'bar')
        self.assertTrue('created' not in resp.json)

    def testJobProgressAndNotifications(self):
        job = self.model('job', 'jobs').createJob(
            title='a job', type='t', user=self.users[1], public=True)

        path = '/job/%s' % job['_id']
        resp = self.request(path)
        self.assertEqual(resp.json['progress'], None)
        self.assertEqual(resp.json['timestamps'], [])

        resp = self.request(path, method='PUT', user=self.users[1], params={
            'progressTotal': 100,
            'progressCurrent': 3,
            'progressMessage': 'Started',
            'notify': 'false',
            'status': JobStatus.RUNNING
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
        self.assertEqual(
            resp.json['timestamps'][0]['status'], JobStatus.RUNNING)
        self.assertIn('time', resp.json['timestamps'][0])

        # If the status does not change on update, no timestamp should be added
        resp = self.request(path, method='PUT', user=self.users[1], params={
            'status': JobStatus.RUNNING
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['timestamps']), 1)
        self.assertEqual(
            resp.json['timestamps'][0]['status'], JobStatus.RUNNING)

        # We passed notify=false, so we should not have any notifications
        resp = self.request(path='/notification/stream', method='GET',
                            user=self.users[1], isJson=False,
                            params={'timeout': 0})
        messages = self.getSseMessages(resp)
        self.assertEqual(len(messages), 0)

        # Update progress with notify=true (the default)
        resp = self.request(path, method='PUT', user=self.users[1], params={
            'progressCurrent': 50,
            'progressMessage': 'Something bad happened',
            'status': JobStatus.ERROR
        })
        self.assertStatusOk(resp)
        self.assertNotEqual(resp.json['progress']['notificationId'], None)

        # We should now see two notifications (job status + progress)
        resp = self.request(path='/notification/stream', method='GET',
                            user=self.users[1], isJson=False,
                            params={'timeout': 0})
        messages = self.getSseMessages(resp)
        job = self.model('job', 'jobs').load(job['_id'], force=True)
        self.assertEqual(len(messages), 2)
        statusNotify = messages[0]
        progressNotify = messages[1]

        self.assertEqual(statusNotify['type'], 'job_status')
        self.assertEqual(statusNotify['data']['_id'], str(job['_id']))
        self.assertEqual(int(statusNotify['data']['status']), JobStatus.ERROR)
        self.assertTrue('kwargs' not in statusNotify['data'])

        self.assertEqual(progressNotify['type'], 'progress')
        self.assertEqual(progressNotify['data']['title'], job['title'])
        self.assertEqual(progressNotify['data']['current'], float(50))
        self.assertEqual(progressNotify['data']['state'], 'error')
        self.assertEqual(progressNotify['_id'],
                         str(job['progress']['notificationId']))

    def testDotsInKwargs(self):
        kwargs = {
            '$key.with.dots': 'value',
            'foo': [{
                'moar.dots': True
            }]
        }
        job = self.model('job', 'jobs').createJob(
            title='dots', type='x', user=self.users[0], kwargs=kwargs)

        # Make sure we can update a job and notification creation works
        self.model('job', 'jobs').updateJob(
            job, status=JobStatus.ERROR, notify=True)

        self.assertEqual(job['kwargs'], kwargs)

        resp = self.request('/job/%s' % job['_id'], user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['kwargs'], kwargs)

        job = self.model('job', 'jobs').load(job['_id'], force=True)
        self.assertEqual(job['kwargs'], kwargs)
        job = self.model('job', 'jobs').filter(job, self.users[0])
        self.assertEqual(job['kwargs'], kwargs)
        job = self.model('job', 'jobs').filter(job, self.users[1])
        self.assertFalse('kwargs' in job)

    def testLocalJob(self):
        job = self.model('job', 'jobs').createLocalJob(
            title='local', type='local', user=self.users[0], kwargs={
                'hello': 'world'
            }, module='plugin_tests.local_job_impl')

        self.model('job', 'jobs').scheduleJob(job)

        job = self.model('job', 'jobs').load(job['_id'], force=True,
                                             includeLog=True)
        self.assertEqual(job['log'], ['job ran!'])

        job = self.model('job', 'jobs').createLocalJob(
            title='local', type='local', user=self.users[0], kwargs={
                'hello': 'world'
            }, module='plugin_tests.local_job_impl', function='fail')

        self.model('job', 'jobs').scheduleJob(job)

        job = self.model('job', 'jobs').load(job['_id'], force=True,
                                             includeLog=True)
        self.assertEqual(job['log'], ['job failed'])

    def testValidateCustomStatus(self):
        jobModel = self.model('job', 'jobs')
        job = jobModel.createJob(title='test', type='x', user=self.users[0])

        def validateStatus(event):
            if event.info == 1234:
                event.preventDefault().addResponse(True)

        with self.assertRaises(ValidationException):
            jobModel.updateJob(job, status=1234)  # Should fail

        with events.bound('jobs.status.validate', 'test', validateStatus):
            jobModel.updateJob(job, status=1234)  # Should work

            with self.assertRaises(ValidationException):
                jobModel.updateJob(job, status=4321)  # Should fail
