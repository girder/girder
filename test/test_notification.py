import asyncio
import time

import pytest
import websockets

from girder.models.token import Token
from girder.notification import Notification


async def _recv_notification(ws, user, data, timeout):
    """
    Publish a notification until the socket receives one, or the deadline
    passes.

    The server subscribes to redis asynchronously after the websocket is
    connected, so a notification published immediately after connecting can be
    published before the subscription exists and be lost.  Republishing until a
    message arrives makes this robust against that race without relying on a
    fixed sleep.
    """
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError('Timed out waiting for a websocket notification')
        Notification(type='test', data=data, user=user).flush()
        try:
            return await asyncio.wait_for(ws.recv(), timeout=min(remaining, 1))
        except asyncio.TimeoutError:
            continue


async def _drain_notifications(ws):
    """Discard any notifications already queued on the socket."""
    while True:
        try:
            await asyncio.wait_for(ws.recv(), timeout=0.1)
        except asyncio.TimeoutError:
            return


@pytest.mark.asyncio
async def test_notification_websocket_timeout(db, asgiBoundServer, admin):
    """
    Test that WebSocket notifications don't disconnect after 5 seconds when
    socket_timeout is set to None.
    """
    token = Token().createToken(admin, days=1)
    ws_url = f'ws://localhost:{asgiBoundServer.boundPort}/notifications/me?token={token["_id"]}'
    async with websockets.connect(ws_url) as ws:
        # Send a notification and verify it's received.  Retrying the publish
        # also guarantees the server-side redis subscription is established.
        received = await _recv_notification(ws, admin, {'a': 'b'}, timeout=10)
        assert received is not None, 'Failed to receive initial notification'

        # The redis connection uses no socket timeout.  Wait longer than redis'
        # 5 second default and verify the socket still delivers notifications.
        await asyncio.sleep(7)
        await _drain_notifications(ws)
        received = await _recv_notification(ws, admin, {'a': 'c'}, timeout=10)
        assert received is not None, 'Failed to receive notification'
