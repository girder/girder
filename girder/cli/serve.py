import tempfile

import cherrypy
import click

from girder import plugin
from girder.utility import server
from girder.constants import ServerMode
from girder.models.assetstore import Assetstore
from girder.models.file import File


@click.command(name='serve', short_help='Run the Girder server.', help='Run the Girder server.')
@click.option('--dev', default=False, is_flag=True, help='Alias for --mode=development')
@click.option('--mode', type=click.Choice([
    ServerMode.PRODUCTION,
    ServerMode.DEVELOPMENT,
    ServerMode.TESTING
    ]), default=ServerMode.DEVELOPMENT, show_default=True, help='Specify the server mode')
@click.option('-d', '--database', default=cherrypy.config['database']['uri'],
              show_default=True, help='The database URI to connect to')
@click.option('-H', '--host', default=cherrypy.config['server.socket_host'],
              show_default=True, help='The interface to bind to')
@click.option('-p', '--port', type=int, default=cherrypy.config['server.socket_port'],
              show_default=True, help='The port to bind to')
@click.option('--with-temp-assetstore', default=False, is_flag=True,
              help='Create a temporary assetstore for this server instance')
def main(dev: bool, mode: str, database: str, host: str, port: int, with_temp_assetstore: bool):
    if dev and mode:
        raise click.ClickException('Conflict between --dev and --mode')
    if dev:
        mode = ServerMode.DEVELOPMENT

    # If the user provides no options, the existing config values get re-set through click
    cherrypy.config['database']['uri'] = database
    cherrypy.config['server.socket_host'] = host
    cherrypy.config['server.socket_port'] = port

    app_info = server.create_app(mode)
    plugin._loadPlugins(app_info)

    cherrypy.tree = app_info['serverRoot']
    cherrypy.engine.signal_handler.subscribe()
    cherrypy.engine.start()

    if with_temp_assetstore:
        with tempfile.TemporaryDirectory() as tempdir:
            assetstore = Assetstore().createFilesystemAssetstore(
                name=tempdir,
                root=tempdir,
            )
            try:
                cherrypy.engine.block()
            finally:
                # Delete all files in the assetstore
                File().removeWithQuery({
                    'assetstoreId': assetstore['_id']
                })
                Assetstore().remove(assetstore)
    else:
        cherrypy.engine.block()
