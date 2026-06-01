import asyncio

import pytest
import websockets

from girder.models.token import Token
from girder.notification import Notification


@pytest.mark.asyncio
async def test_notification_websocket_timeout(db, asgiBoundServer, admin):
    """
    Test that WebSocket notifications don't disconnect after 5 seconds when
    socket_timeout is set to None.
    """
    token = Token().createToken(admin, days=1)
    ws_url = f'ws://localhost:{asgiBoundServer.boundPort}/notifications/me?token={token["_id"]}'
    async with websockets.connect(ws_url) as ws:
        # Send a notification and verify it's received
        Notification(type='test', data={'a': 'b'}, user=admin).flush()
        await asyncio.sleep(1)  # Allow time for notification to be processed
        received = await asyncio.wait_for(ws.recv(), timeout=2)
        # assert received is not None, 'Failed to receive initial notification'
        # redis 8 defaults to a 5 second timeout
        await asyncio.sleep(7)
        Notification(type='test', data={'a': 'c'}, user=admin).flush()
        await asyncio.sleep(1)  # Allow time for notification to be processed
        received = await asyncio.wait_for(ws.recv(), timeout=2)
        assert received is not None, 'Failed to receive notification'
