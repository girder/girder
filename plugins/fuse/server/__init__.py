import cherrypy

from girder import logger
from girder.exceptions import FilePathException
from girder.models.file import File
from girder.utility import config, mkdir, abstract_assetstore_adapter

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
    return File().getLocalFilePath(file)


def getFuseFilePath(file):
    """
    Given a file resource, return a path on the main FUSE file system.

    :param file: file resource document.
    :returns: a path on the local file system.
    """
    return server_fuse.getServerFusePath(MAIN_FUSE_KEY, 'file', file)


def makeLocalFilePathMethod(func):
    """
    Return a method that if a FilePathException would be raised and a fuse file
    exists, the fuse path is returned instead.
    This wrapping function acts much like Python 3's functools.partialmethod.

    :returns: the wrapped getLocalFilePath method.
    """
    def getLocalFilePath(self, file):
        """
        This replaces getLocalFilePath in the abstract assetstore adapter to
        use the FUSE path if available.  For adapters that override that
        method, this will do nothing.

        :param file: file resource document.
        :returns: a path on the local file system.
        """
        try:
            return func(self, file)
        except FilePathException:
            path = getFuseFilePath(file)
            if path:
                return path
            raise
    return getLocalFilePath


def load(info):
    startFromConfig()

    adapter = abstract_assetstore_adapter.AbstractAssetstoreAdapter
    adapter.getLocalFilePath = makeLocalFilePathMethod(adapter.getLocalFilePath)
