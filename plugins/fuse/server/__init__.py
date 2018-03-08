import cherrypy

from girder import logger
from girder.models.file import File
from girder.utility import config, mkdir

from . import server_fuse


MAIN_FUSE_KEY = '_server'


def startFromConfig():
    """
    Check if the config file has a section [server_fuse] and key "path".  If
    so, mount a FUSE at the specified path without using access validation.

    :returns: True if a mount was made.  False if an error was raised.  None
        if no mount was attemped.
    """
    cfg = config.getConfig().get('server_fuse', {})
    path = cfg.get('path')
    cherrypy.engine.subscribe('stop', server_fuse.unmountAll)

    if path:
        try:
            mkdir(path)
            return server_fuse.mountServerFuse(MAIN_FUSE_KEY, path, force=True)
        except Exception:
            logger.exception('Can\'t mount resource fuse: %s' % path)
            return False


def getFilePath(file):
    """
    Given a file resource, return a path on the local file system.  For
    assetstores that have a fullPath method, this returns the results of that
    call.  Otherwise, it returns a path on the main mounted FUSE.

    :param file: file resource document.
    :returns: a path on the local file system.
    """
    adapter = File().getAssetstoreAdapter(file)
    if callable(getattr(adapter, 'fullPath', None)):
        return adapter.fullPath(file)
    return server_fuse.getServerFusePath(MAIN_FUSE_KEY, 'file', file)


def getFuseFilePath(file):
    """
    Given a file resource, return a path on the main FUSE file system.

    :param file: file resource document.
    :returns: a path on the local file system.
    """
    return server_fuse.getServerFusePath(MAIN_FUSE_KEY, 'file', file)


def load(info):
    startFromConfig()
