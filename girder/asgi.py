import logging
from contextlib import asynccontextmanager

from starlette.middleware.wsgi import WSGIMiddleware
from starlette.routing import Mount, WebSocketRoute
from starlette.applications import Starlette

from girder.wsgi import app as wsgi_app
from girder.notification import UserNotificationsSocket


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
