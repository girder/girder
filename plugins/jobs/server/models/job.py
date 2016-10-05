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

import datetime
import six
from bson import json_util

from girder import events
from girder.constants import AccessType, SortDir
from girder.models.model_base import AccessControlledModel, ValidationException
from girder.plugins.jobs.constants import JobStatus, JOB_HANDLER_LOCAL


class Job(AccessControlledModel):
    def initialize(self):
        self.name = 'job'
        compoundSearchIndex = (
            ('userId', SortDir.ASCENDING),
            ('created', SortDir.DESCENDING)
        )
        self.ensureIndices([(compoundSearchIndex, {})])

        self.exposeFields(level=AccessType.READ, fields={
            'title', 'type', 'created', 'interval', 'when', 'status',
            'progress', 'log', 'meta', '_id', 'public', 'async', 'updated', 'timestamps'})

        self.exposeFields(level=AccessType.SITE_ADMIN, fields={'args', 'kwargs'})

    def validate(self, job):
        self._validateStatus(job['status'])

        return job

    def _validateStatus(self, status):
        if not JobStatus.isValid(status):
            raise ValidationException(
                'Invalid job status %s.' % status, field='status')

    def list(self, user=None, limit=0, offset=0, sort=None, currentUser=None):
        """
        List a page of jobs for a given user.

        :param user: The user who owns the job.
        :type user: dict or None
        :param limit: The page limit.
        :param offset: The page offset
        :param sort: The sort field.
        :param currentUser: User for access filtering.
        """
        userId = user['_id'] if user else None
        cursor = self.find({'userId': userId}, sort=sort)

        for r in self.filterResultsByPermission(cursor=cursor, user=currentUser,
                                                level=AccessType.READ,
                                                limit=limit, offset=offset):
            yield r

    def cancelJob(self, job):
        """
        Revoke/cancel a job. This simply triggers the jobs.cancel event and
        sets the job status to CANCELED. If one of the event handlers
        calls preventDefault() on the event, this job will *not* be put into
        the CANCELED state.

        :param job: The job to cancel.
        """
        event = events.trigger('jobs.cancel', info=job)

        if not event.defaultPrevented:
            job = self.updateJob(job, status=JobStatus.CANCELED)

        return job

    def createLocalJob(self, module, function=None, **kwargs):
        """
        Takes the same keyword arguments as :py:func:`createJob`, except this
        sets the handler to the local handler and takes additional parameters
        to specify the module and function that should be run.

        :param module: The name of the python module to run.
        :type module: str
        :param function: Function name within the module to run. If not passed,
            the default name of "run" will be used.
        :type function: str or None
        :returns: The job that was created.
        """
        kwargs['handler'] = JOB_HANDLER_LOCAL
        kwargs['save'] = False

        job = self.createJob(**kwargs)

        job['module'] = module

        if function is not None:
            job['function'] = function

        return self.save(job)

    def createJob(self, title, type, args=(), kwargs=None, user=None, when=None,
                  interval=0, public=False, handler=None, async=False,
                  save=True, otherFields=None):
        """
        Create a new job record.

        :param title: The title of the job.
        :type title: str
        :param type: The type of the job.
        :type type: str
        :param args: Positional args of the job payload.
        :type args: list or tuple
        :param kwargs: Keyword arguments of the job payload.
        :type kwargs: dict
        :param user: The user creating the job.
        :type user: dict or None
        :param when: Minimum start time for the job (UTC).
        :type when: datetime
        :param interval: If this job should be recurring, set this to a value
            in seconds representing how often it should occur. Set to <= 0 for
            jobs that should only be run once.
        :type interval: int
        :param public: Public read access flag.
        :type public: bool
        :param handler: If this job should be handled by a specific handler,
            use this field to store that information.
        :param externalToken: If an external token was created for updating this
        job, pass it in and it will have the job-specific scope set.
        :type externalToken: token (dict) or None.
        :param async: Whether the job is to be run asynchronously. For now this
            only applies to jobs that are scheduled to run locally.
        :type async: bool
        :param save: Whether the documented should be saved to the database.
        :type save: bool
        :param otherFields: Any additional fields to set on the job.
        :type otherFields: dict
        """
        now = datetime.datetime.utcnow()

        if when is None:
            when = now

        if kwargs is None:
            kwargs = {}

        otherFields = otherFields or {}

        job = {
            'title': title,
            'type': type,
            'args': args,
            'kwargs': kwargs,
            'created': now,
            'updated': now,
            'when': when,
            'interval': interval,
            'status': JobStatus.INACTIVE,
            'progress': None,
            'log': [],
            'meta': {},
            'handler': handler,
            'async': async,
            'timestamps': []
        }

        job.update(otherFields)

        self.setPublic(job, public=public)

        if user:
            job['userId'] = user['_id']
            self.setUserAccess(job, user=user, level=AccessType.ADMIN)

        if save:
            job = self.save(job)

        return job

    def save(self, job, *args, **kwargs):
        """
        We extend save so that we can serialize the kwargs before sending them
        to the database. This will allow kwargs with $ and . characters in the
        keys.
        """
        deserialized = job['kwargs']
        job['kwargs'] = json_util.dumps(job['kwargs'])
        job = AccessControlledModel.save(self, job, *args, **kwargs)
        job['kwargs'] = deserialized
        return job

    def find(self, *args, **kwargs):
        """
        Overrides the default find behavior to exclude the log by default.

        :param includeLog: Whether to include the log field in the documents.
        :type includeLog: bool
        """
        kwargs['fields'] = self._computeFields(kwargs)
        return super(Job, self).find(*args, **kwargs)

    def load(self, *args, **kwargs):
        """
        We extend load to deserialize the kwargs back into a dict since we
        serialized them on the way into the database.

        :param includeLog: Whether to include the log field in the document.
        :type includeLog: bool
        """
        kwargs['fields'] = self._computeFields(kwargs)
        job = super(Job, self).load(*args, **kwargs)

        if job and isinstance(job['kwargs'], six.string_types):
            job['kwargs'] = json_util.loads(job['kwargs'])
        if job and isinstance(job.get('log'), six.string_types):
            # Legacy support: log used to be just a string, but we want to
            # consistently return a list of strings now.
            job['log'] = [job['log']]

        return job

    def scheduleJob(self, job):
        """
        Trigger the event to schedule this job. Other plugins are in charge of
        actually scheduling and/or executing the job, except in the case when
        the handler is 'local'.
        """
        if job.get('async') is True:
            events.daemon.trigger('jobs.schedule', info=job)
        else:
            events.trigger('jobs.schedule', info=job)

    def createJobToken(self, job, days=7):
        """
        Create a token that can be used just for the management of an individual
        job, e.g. updating job info, progress, logs, status.
        """
        return self.model('token').createToken(
            days=days, scope='jobs.job_' + str(job['_id']))

    def updateJob(self, job, log=None, overwrite=False, status=None,
                  progressTotal=None, progressCurrent=None, notify=True,
                  progressMessage=None, otherFields=None):
        """
        Update an existing job. Any of the updateable fields that are set to None in the kwargs of
        this method will not be modified. If you set progress information on the job for the first
        time and set notify=True, a new notification record for the job progress will be created.
        If notify=True, job status changes will also create a notification with type="job_status",
        and log changes will create a notification with type="job_log".

        :param job: The job document to update.
        :param log: Message to append to the job log. If you wish to overwrite
            instead of append, pass overwrite=True.
        :type log: str
        :param overwrite: Whether to overwrite the log (default is append).
        :type overwrite: bool
        :param status: New status for the job.
        :type status: JobStatus
        :param progressTotal: Max progress value for this job.
        :param otherFields: Any additional fields to set on the job.
        :type otherFields: dict
        """
        event = events.trigger('jobs.job.update', {
            'job': job,
            'params': {
                'log': log,
                'overwrite': overwrite,
                'status': status,
                'progressTotal': progressTotal,
                'progressMessage': progressMessage,
                'otherFields': otherFields
            }
        })

        if event.defaultPrevented:
            return job

        now = datetime.datetime.utcnow()
        user = None
        otherFields = otherFields or {}

        if job['userId']:
            user = self.model('user').load(job['userId'], force=True)

        updates = {
            '$push': {},
            '$set': {}
        }

        if log is not None:
            self._updateLog(job, log, overwrite, now, notify, user, updates)
        if status is not None:
            self._updateStatus(job, status, now, notify, user, updates)
        if progressMessage is not None or progressCurrent is not None or progressTotal is not None:
            self._updateProgress(
                job, progressTotal, progressCurrent, progressMessage, notify, user, updates)

        for k, v in six.viewitems(otherFields):
            job[k] = v
            updates['$set'][k] = v

        if updates['$set'] or updates['$push']:
            if not updates['$push']:
                del updates['$push']
            job['updated'] = now
            updates['$set']['updated'] = now

            self.update({'_id': job['_id']}, update=updates, multi=False)

            events.trigger('jobs.job.update.after', {
                'job': job
            })

        return job

    def _updateLog(self, job, log, overwrite, now, notify, user, updates):
        """Helper for updating a job's log."""
        if overwrite:
            updates['$set']['log'] = [log]
        else:
            updates['$push']['log'] = log
        if notify and user:
            expires = now + datetime.timedelta(seconds=30)
            self.model('notification').createNotification(
                type='job_log', data={
                    '_id': job['_id'],
                    'overwrite': overwrite,
                    'text': log
                }, user=user, expires=expires)

    def _updateStatus(self, job, status, now, notify, user, updates):
        """Helper for updating job progress information."""
        try:
            status = int(status)
        except ValueError:
            # Allow non int states
            pass

        self._validateStatus(status)

        if status != job['status']:
            job['status'] = status
            updates['$set']['status'] = status
            ts = {
                'status': status,
                'time': now
            }
            job['timestamps'].append(ts)
            updates['$push']['timestamps'] = ts

            if notify and user:
                expires = now + datetime.timedelta(seconds=30)
                filtered = self.filter(job, user)
                filtered.pop('kwargs', None)
                filtered.pop('log', None)
                self.model('notification').createNotification(
                    type='job_status', data=filtered, user=user, expires=expires)

    def _updateProgress(self, job, total, current, message, notify, user, updates):
        """Helper for updating job progress information."""
        state = JobStatus.toNotificationStatus(job['status'])

        if current is not None:
            current = float(current)
        if total is not None:
            total = float(total)

        if job['progress'] is None:
            if notify and job['userId']:
                notification = self._createProgressNotification(
                    job, total, current, state, message)
                notificationId = notification['_id']
            else:
                notificationId = None
            job['progress'] = {
                'message': message,
                'total': total,
                'current': current,
                'notificationId': notificationId
            }
            updates['$set']['progress'] = job['progress']
        else:
            if total is not None:
                job['progress']['total'] = total
                updates['$set']['progress.total'] = total
            if current is not None:
                job['progress']['current'] = current
                updates['$set']['progress.current'] = current
            if message is not None:
                job['progress']['message'] = message
                updates['$set']['progress.message'] = message

            if notify and user:
                if job['progress']['notificationId'] is None:
                    notification = self._createProgressNotification(
                        job, total, current, state, message, user)
                    nid = notification['_id']
                    job['progress']['notificationId'] = nid
                    updates['$set']['progress.notificationId'] = nid
                else:
                    notification = self.model('notification').load(
                        job['progress']['notificationId'])

                self.model('notification').updateProgress(
                    notification, state=state,
                    message=job['progress']['message'],
                    current=job['progress']['current'],
                    total=job['progress']['total'])

    def _createProgressNotification(self, job, total, current, state, message,
                                    user=None):
        if not user:
            user = self.model('user').load(job['userId'], force=True)
        # TODO support channel-based notifications for jobs. For
        # right now we'll just go through the user.
        return self.model('notification').initProgress(
            user, job['title'], total, state=state, current=current,
            message=message, estimateTime=False)

    def filter(self, doc, user=None, additionalKeys=None):
        """
        Overrides the parent ``filter`` method to also deserialize the ``kwargs``
        field if it is still in serialized form. This is handled in ``load``, but
        required here also for fetching lists of jobs.
        """
        doc = super(Job, self).filter(doc, user, additionalKeys=additionalKeys)

        if 'kwargs' in doc and isinstance(doc['kwargs'], six.string_types):
            doc['kwargs'] = json_util.loads(doc['kwargs'])

        return doc

    def _computeFields(self, kwargs, includeLogDefault=False):
        """
        Helper to compute the projection operator for default log exclusion.
        """
        fields = kwargs.get('fields')
        if fields is None and not kwargs.pop('includeLog', includeLogDefault):
            fields = {'log': False}
        return fields
