from asgiref.wsgi import WsgiToAsgi

from girder.wsgi import app as wsgi_app

app = WsgiToAsgi(wsgi_app)
