# -*- coding: utf-8 -*-
import cherrypy
import girder
from girder.utility import server

cherrypy.config.update({'engine.autoreload.on': False,
                        'environment': 'embedded'})
cherrypy.config['server'].update({'disable_event_daemon': True})

# TODO The below line can be removed if we do away with girder.logprint
girder._quiet = True  # This means we won't duplicate messages to stdout/stderr
_formatter = girder.LogFormatter('[%(asctime)s] %(levelname)s: %(message)s')
_handler = cherrypy._cplogging.WSGIErrorHandler()
_handler.setFormatter(_formatter)
girder.logger.addHandler(_handler)

# 'application' is the default callable object for WSGI implementations, see PEP 3333 for more.
server.setup()
application = cherrypy.tree

cherrypy.server.unsubscribe()
cherrypy.engine.start()
