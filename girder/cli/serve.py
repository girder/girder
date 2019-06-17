# -*- coding: utf-8 -*-
import cherrypy
import click
import six

from girder import _attachFileLogHandlers
from girder.utility import server
from girder.constants import PRODUCTION_MODE, DEVELOPMENT_MODE, TESTING_MODE


@click.command(name='serve', short_help='Run the Girder server.', help='Run the Girder server.')
@click.option('--mode', type=click.Choice([PRODUCTION_MODE, DEVELOPMENT_MODE, TESTING_MODE]),
              default=PRODUCTION_MODE, show_default=True, help='Specify the server mode')
@click.option('-d', '--database', default=cherrypy.config['database']['uri'],
              show_default=True, help='The database URI to connect to')
@click.option('-H', '--host', default=cherrypy.config['server.socket_host'],
              show_default=True, help='The interface to bind to')
@click.option('-p', '--port', type=int, default=cherrypy.config['server.socket_port'],
              show_default=True, help='The port to bind to')
def main(mode, database, host, port):
    # If the user provides no options, the existing config values get re-set through click
    cherrypy.config['database']['uri'] = database
    if six.PY2:
        # On Python 2, click returns the value as unicode and CherryPy expects a str
        # Keep this conversion explicitly for Python 2 only, so it can be removed when Python 2
        # support is dropped
        host = str(host)
    cherrypy.config['server.socket_host'] = host
    cherrypy.config['server.socket_port'] = port

    _attachFileLogHandlers()
    server.setup(mode)

    cherrypy.engine.start()
    cherrypy.engine.block()
