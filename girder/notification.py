import asyncio
import datetime
import functools
import json
import logging
import os
import time
import uuid

import redis
import redis.asyncio as aioredis
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket

from girder.constants import TokenScope
from girder.models.token import Token

logger = logging.getLogger(__name__)


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


@functools.lru_cache
def _redis_client_async() -> aioredis.Redis:
    url = os.environ.get('GIRDER_NOTIFICATION_REDIS_URL', 'redis://localhost:6379')
    return aioredis.Redis.from_url(url)


@functools.lru_cache
def _redis_client_sync() -> redis.Redis:
    url = os.environ.get('GIRDER_NOTIFICATION_REDIS_URL', 'redis://localhost:6379')
    return redis.Redis.from_url(url)


class UserNotificationsSocket(WebSocketEndpoint):
    user_id: str

    async def on_connect(self, websocket):
        token_id = websocket.query_params.get('token')
        if not token_id:
            await websocket.close(code=3000, reason='Token is required')
            return

        token = Token().load(token_id, force=True, objectId=False)
        if (
            token is None
            or token['expires'] < datetime.datetime.now(datetime.timezone.utc)
            or 'userId' not in token
            or not Token().hasScope(token, TokenScope.USER_AUTH)
        ):
            await websocket.close(code=3000, reason='Invalid token')
            return

        await websocket.accept()

        self.user_id = token['userId']
        self.pubsub = _redis_client_async().pubsub()
        await self.pubsub.subscribe(f'user_{self.user_id}')

        self.listen_task = asyncio.create_task(self.listen_and_forward(websocket))

    async def listen_and_forward(self, websocket: WebSocket):
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    await websocket.send_text(message['data'].decode())
        except asyncio.CancelledError:
            pass
        finally:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()

    async def on_disconnect(self, websocket, close_code):
        if hasattr(self, 'listen_task'):
            self.listen_task.cancel()
            await self.listen_task


class Notification:
    def __init__(self, type: str, data: dict, user: dict, **payload):
        """
        Create a notification for a specific user's notification channel.

        :param type: The notification type.
        :param data: The notification payload.
        :param user: User to send the notification to.
        """
        self._payload = {
            'type': type,
            'data': data,
            **payload,
        }
        self._user = user

    def flush(self):
        msg = json.dumps(self._payload, default=str)

        try:
            _redis_client_sync().publish(f'user_{self._user["_id"]}', msg)
        except redis.RedisError:
            logger.exception('Error flushing notification to redis')

    @classmethod
    def initProgress(cls, user, title, total=0, state=ProgressState.ACTIVE,
                     current=0, message='', estimateTime=True, resource=None,
                     resourceName=None, _id=None) -> 'Notification':
        """
        Create a "progress" type notification that can be updated anytime there
        is progress on some task. It is the caller's responsibility to call `flush`
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
        :param _id: the unique ID of this progress stream. If not provided, a random UUID will
            be used. Only pass this if you need to update the same progress stream from multiple
            request contexts or task contexts, where it's not possible to reuse the same
            instance of this class.
        """
        if _id is None:
            _id = str(uuid.uuid4())

        data = {
            'title': title,
            'total': total,
            'current': current,
            'state': state,
            'message': message,
            'resource': resource,
            'resourceName': resourceName,
        }

        return cls(
            'progress', data, user, estimateTime=estimateTime, startTime=time.time(), _id=_id
        )

    def updateProgress(self, *, increment: int = None, **kwargs):
        """
        Send a progress update message to any listeners of this notification.

        :param increment: The amount to increment the current progress by.
        :param kwargs: Any other fields to update in the progress message payload.
        """
        if increment is not None:
            self._payload['data']['current'] += increment

        self._payload['data'].update(kwargs)

        current, total = self._payload['data']['current'], self._payload['data']['total']

        if self._payload['estimateTime'] and total > 0 and current > 0:
            self._payload['updatedTime'] = time.time()
            self._payload['estimatedTotalTime'] = (
                total * (self._payload['updatedTime'] - self._payload['startTime']) / current
            )

        self.flush()
