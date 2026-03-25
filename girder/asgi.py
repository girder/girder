import logging
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.middleware.wsgi import WSGIMiddleware
from starlette.routing import Mount, WebSocketRoute

from girder.notification import UserNotificationsSocket
from girder.wsgi import app as wsgi_app


@asynccontextmanager
async def lifespan(app):
    logger = logging.getLogger(__name__)
    logger.info('Girder server running')
    yield


app = Starlette(
    lifespan=lifespan,
    routes=[
        WebSocketRoute('/notifications/me', UserNotificationsSocket),
        Mount('/', app=WSGIMiddleware(wsgi_app)),
    ],
)
