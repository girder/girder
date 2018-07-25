#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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
import time

from .model_base import Model


class ProgressState(object):
    """
    Enum of possible progress states for progress records.
    """
    QUEUED = 'queued'
    ACTIVE = 'active'
    SUCCESS = 'success'
    ERROR = 'error'

    @classmethod
    def isComplete(cls, state):
        return state == cls.SUCCESS or state == cls.ERROR


class Notification(Model):
    """
    This model is used to represent a notification that should be streamed
    to a specific user in some way. Each notification contains a
    type field indicating what kind of notification it is, a userId field
    indicating which user the notification should be sent to, a data field
    representing the payload of the notification, a time field indicating the
    time at which the event happened, and an optional expires field indicating
    at what time the notification should be deleted from the database.
    """
    def initialize(self):
        self.name = 'notification'
        self.ensureIndices(('userId', 'time', 'updated', 'tokenId'))
        self.ensureIndex(('expires', {'expireAfterSeconds': 0}))

    def validate(self, doc):
        return doc

    def createNotification(self, type, data, user, expires=None, token=None):
        """
        Create a generic notification.

        :param type: The notification type.
        :type type: str
        :param data: The notification payload.
        :param user: User to send the notification to.
        :type user: dict
        :param expires: Expiration date (for transient notifications).
        :type expires: datetime.datetime
        :param token: Set this if the notification should correspond to a token
            instead of a user.
        :type token: dict
        """
        now = datetime.datetime.utcnow()
        currentTime = time.time()
        doc = {
            'type': type,
            'data': data,
            'time': now,
            'updated': now,
            'startTime': currentTime,
            'updatedTime': currentTime
        }
        if user:
            doc['userId'] = user['_id']
        elif token:
            doc['tokenId'] = token['_id']

        if expires is not None:
            doc['expires'] = expires

        return self.save(doc)

    def initProgress(self, user, title, total=0, state=ProgressState.ACTIVE,
                     current=0, message='', token=None, estimateTime=True, resource=None,
                     resourceName=None):
        """
        Create a "progress" type notification that can be updated anytime there
        is progress on some task. Progress records that are not updated for more
        than one hour will be deleted. The "time" field of a progress record
        indicates the time the task was started.

        :param user: the user associated with this notification.  If this is
            None, a session token must be specified.
        :param title: The title of the task. This should not change over the
            course of the task. (e.g. 'Deleting folder "foo"')
        :type title: str
        :param total: Some numeric value representing the total task length. By
            convention, setting this <= 0 means progress on this task is
            indeterminate.
        :type total: int, long, or float
        :param state: Represents the state of the underlying task execution.
        :type state: ProgressState enum value.
        :param current: Some numeric value representing the current progress of
            the task (relative to total).
        :type current: int, long, or float
        :param message: Message corresponding to the current state of the task.
        :type message: str
        :param token: if the user is None, associate this notification with the
            specified session token.
        :param estimateTime: if True, generate an estimate of the total time
            the task will take, if possible.  If False, never generate a time
            estimate.
        :param resource: a partial or complete resource that the notification is
            associated with. This must at a minimum include the id of the resource.
        :param resourceName: the type of resource the notification is associated with.
        """
        data = {
            'title': title,
            'total': total,
            'current': current,
            'state': state,
            'message': message,
            'estimateTime': estimateTime,
            'resource': resource,
            'resourceName': resourceName
        }
        expires = datetime.datetime.utcnow() + datetime.timedelta(hours=1)

        return self.createNotification('progress', data, user, expires,
                                       token=token)

    def updateProgress(self, record, save=True, **kwargs):
        """
        Update an existing progress record.

        :param record: The existing progress record to update.
        :type record: dict
        :param total: Some numeric value representing the total task length. By
            convention, setting this <= 0 means progress on this task is
            indeterminate. Generally this shouldn't change except in cases where
            progress on a task switches between indeterminate and determinate
            state.
        :type total: int, long, or float
        :param state: Represents the state of the underlying task execution.
        :type state: ProgressState enum value.
        :param current: Some numeric value representing the current progress
            of the task (relative to total).
        :type current: int, long, or float
        :param increment: Amount to increment the progress by. Don't pass both
            current and increment together, as that behavior is undefined.
        :type increment: int, long, or float
        :param message: Message corresponding to the current state of the task.
        :type message: str
        :param expires: Set a custom (UTC) expiration time on the record.
            Default is one hour from the current time.
        :type expires: datetime
        :param save: Whether to save the record to the database.
        :type save: bool
        """
        if 'increment' in kwargs:
            record['data']['current'] += kwargs['increment']

        for field, value in six.viewitems(kwargs):
            if field in ('total', 'current', 'state', 'message'):
                record['data'][field] = value

        now = datetime.datetime.utcnow()

        if 'expires' in kwargs:
            expires = kwargs['expires']
        else:
            expires = now + datetime.timedelta(hours=1)

        record['updated'] = now
        record['expires'] = expires
        record['updatedTime'] = time.time()
        if save:
            # Only update the time estimate if we are also saving
            if (record['updatedTime'] > record['startTime'] and
                    record['data']['estimateTime']):
                if 'estimatedTotalTime' in record:
                    del record['estimatedTotalTime']
                try:
                    total = float(record['data']['total'])
                    current = float(record['data']['current'])
                    if total >= current and total > 0 and current > 0:
                        record['estimatedTotalTime'] = (total * (
                            record['updatedTime'] - record['startTime']) /
                            current)
                except ValueError:
                    pass
            return self.save(record)
        else:
            return record

    def get(self, user, since=None, token=None, sort=None):
        """
        Get outstanding notifications for the given user.

        :param user: The user requesting updates.  None to use the token
            instead.
        :param since: Limit results to entities that have been updated
            since a certain timestamp.
        :type since: datetime
        :param token: if the user is None, the token requesting updated.
        :param sort: Sort field for the database query.
        """
        q = {}
        if user:
            q['userId'] = user['_id']
        else:
            q['tokenId'] = token['_id']

        if since is not None:
            q['updated'] = {'$gt': since}

        return self.find(q, sort=sort)
