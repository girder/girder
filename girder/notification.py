import asyncio
import datetime
import functools
import os

import redis.asyncio as aioredis
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket

from girder.constants import TokenScope
from girder.models.token import Token


@functools.cache
def _redis_client() -> aioredis.Redis:
    url = os.environ.get('GIRDER_NOTIFICATION_REDIS_URL', 'redis://localhost:6379')
    return aioredis.Redis.from_url(url)


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
        self.pubsub = _redis_client().pubsub()
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
