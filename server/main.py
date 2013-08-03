import cherrypy
import pymongo
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from api import api_main

class Webroot():
    exposed = True

    def __init__(self):
        #self.conn = pymongo.Connection()
        pass

    def GET(self):
        return cherrypy.lib.static.serve_file(
            os.path.join(ROOT_DIR, 'clients', 'web', 'static', 'index.html'),
            content_type='text/html')

if __name__ == '__main__':
    root = Webroot()
    root = api_main.addApiToNode(root)
    print dir(root)

    appconf = {
        '/' : {
            'request.dispatch' : cherrypy.dispatch.MethodDispatcher(),
            'tools.staticdir.root' : ROOT_DIR
            },
        '/static' : {
            'tools.staticdir.on' : 'True',
            'tools.staticdir.dir' : 'clients/web/static',
            }
        }

    #cherrypy.config.update(sys.argv[1])
    cherrypy.config.update(appconf)

    app = cherrypy.tree.mount(root, '/', appconf)
    #app.merge(sys.argv[1])

    cherrypy.engine.start()
    cherrypy.engine.block()
