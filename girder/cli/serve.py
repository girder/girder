import os
import tempfile

import click
import uvicorn

from girder.constants import ServerMode
from girder.models.assetstore import Assetstore
from girder.models.file import File
from girder.utility import config

_default_db_url = os.environ.get('GIRDER_MONGO_URI', 'mongodb://localhost:27017/girder')
_default_mode = os.environ.get('GIRDER_SERVER_MODE', ServerMode.DEVELOPMENT)


@click.command(name='serve', short_help='Run the Girder server.', help='Run the Girder server.')
@click.option('--mode', type=click.Choice([
    ServerMode.PRODUCTION,
    ServerMode.DEVELOPMENT,
    ServerMode.TESTING
    ]), default=_default_mode, show_default=True, help='Specify the server mode')
@click.option('-d', '--database', default=_default_db_url,
              show_default=True, help='The database URI to connect to')
@click.option('-H', '--host', default='127.0.0.1',
              show_default=True, help='The interface to bind to')
@click.option('-p', '--port', type=int, default=8080,
              show_default=True, help='The port to bind to')
@click.option('--with-temp-assetstore', default=False, is_flag=True,
              help='Create a temporary assetstore for this server instance')
def main(mode: str, database: str, host: str, port: int, with_temp_assetstore: bool):
    # Must set these in env when using `reload=True`, due to uvicorn's use of subprocesses
    os.environ['GIRDER_SERVER_MODE'] = mode
    os.environ['GIRDER_MONGO_URI'] = database
    config.getConfig()['server'] = {'mode': mode}
    config.getConfig()['database']['uri'] = database

    def _run_app():
        uvicorn.run(
            'girder.asgi:app',
            host=host,
            port=port,
            reload=True,
            server_header=False,
            date_header=False,
        )

    if with_temp_assetstore:
        with tempfile.TemporaryDirectory() as tempdir:
            assetstore = Assetstore().createFilesystemAssetstore(
                name=tempdir,
                root=tempdir,
            )
            try:
                _run_app()
            finally:
                # Delete all files in the assetstore
                File().removeWithQuery({
                    'assetstoreId': assetstore['_id']
                })
                Assetstore().remove(assetstore)
    else:
        _run_app()
