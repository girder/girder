import functools
import os
import json

import redis


@functools.cache
def _redis_client() -> redis.Redis:
    url = os.environ.get('GIRDER_NOTIFICATION_REDIS_URL', 'redis://localhost:6379')
    return redis.Redis.from_url(url)


class ProgressState:
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


class Notification:

    def __init__(self, type: str, data: dict, user: dict):
        """
        Create a notification for a specific user's notification channel.

        :param type: The notification type.
        :param data: The notification payload.
        :param user: User to send the notification to.
        """
        self._payload = {
            'type': type,
            'data': data,
        }
        self._user = user

    def flush(self):
        _redis_client().publish(f'user_{self._user["_id"]}', json.dumps(self._payload, default=str))

    @classmethod
    def initProgress(cls, user, title, total=0, state=ProgressState.ACTIVE,
                     current=0, message='', estimateTime=True, resource=None,
                     resourceName=None) -> 'Notification':
        """
        Create a "progress" type notification that can be updated anytime there
        is progress on some task. Progress records that are not updated for more
        than one hour will be deleted. It is the caller's responsibility to call `flush`
        on the returned object to actually send the notification.

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
        payload = {
            'title': title,
            'total': total,
            'current': current,
            'state': state,
            'message': message,
            # TODO remove this from the payload, handle time estimation separately as before
            'estimateTime': estimateTime,
            'resource': resource,
            'resourceName': resourceName
        }

        return cls('progress', payload, user)

    def updateProgress(self, *, increment: int = None, **kwargs):
        """
        Send a progress update message to any listeners of this notification.

        :param increment: The amount to increment the current progress by.
        :param kwargs: Any other fields to update in the progress message payload.
        """
        if increment is not None:
            self._payload['data']['current'] += increment

        self._payload['data'].update(kwargs)

        self.flush()
