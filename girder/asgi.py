from starlette.middleware.wsgi import WSGIMiddleware
from starlette.routing import Mount, WebSocketRoute
from starlette.applications import Starlette

from girder.wsgi import app as wsgi_app
from girder.notification import UserNotificationsSocket


app = Starlette(routes=[
    WebSocketRoute('/notifications/me', UserNotificationsSocket),
    Mount('/', app=WSGIMiddleware(wsgi_app)),
])
