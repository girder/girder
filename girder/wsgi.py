import os

from girder import constants, plugin
from girder.utility.server import create_app

info = create_app(mode=os.environ.get('GIRDER_SERVER_MODE', constants.ServerMode.PRODUCTION))
plugin._loadPlugins(info)
app = info['serverRoot']
