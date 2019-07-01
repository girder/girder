# -*- coding: utf-8 -*-
import cherrypy
import click
import errno
import fuse
import os
import six
import stat
import sys
import threading
import time

import girder
from girder import events, logger, logprint
from girder.exceptions import AccessException, ValidationException
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.setting import Setting
from girder.settings import SettingKey
from girder.utility import config
from girder.utility.model_importer import ModelImporter
from girder.utility import path as path_util
from girder.utility.server import configureServer


class ServerFuse(fuse.Operations):
    """
    This class handles FUSE operations that are non-default.  It exposes the
    Girder resources via the resource path in a read-only manner.  It could be
    extended to expose metadata and other resources by extending the available
    paths.  Files can also be reached via a path shortcut of /file/<id>.
    """

    use_ns = True

    def __init__(self, stat=None):
        """
        Instantiate the operations class.  This sets up tracking for open
        files and file descriptor numbers (handles).

        :param stat: the results of an os.stat call which should be used as
            default values for files in the FUSE.  Files in the FUSE will have
            the same uid, gid, and atime.  If the resource lacks both an
            updated and a created time stamp, the ctime and mtime will also be
            taken from this.  If None, this defaults to the user of the Girder
            process's home directory,
        """
        super(ServerFuse, self).__init__()
        if not stat:
            stat = os.stat(os.path.expanduser('~'))
        # we always set st_mode, st_size, st_ino, st_nlink, so we don't need
        # to track those.
        self._defaultStat = dict((key, getattr(stat, key)) for key in (
            'st_atime', 'st_ctime', 'st_gid', 'st_mtime', 'st_uid', 'st_blksize'))
        self.nextFH = 1
        self.openFiles = {}
        self.openFilesLock = threading.Lock()

    def __call__(self, op, path, *args, **kwargs):
        """
        Generically allow logging and error handling for any operation.

        :param op: operation to perform.
        :param path: path within the fuse (e.g., '', '/user', '/user/<name>',
            etc.).
        """
        logger.debug('-> %s %s %s', op, path, repr(args))
        ret = '[exception]'
        try:
            ret = getattr(self, op)(path, *args, **kwargs)
            return ret
        except Exception as e:
            # Log all exceptions and then reraise them
            if getattr(e, 'errno', None) in (errno.ENOENT, errno.EACCES):
                logger.debug('-- %s %r', op, e)
            else:
                logger.exception('-- %s', op)
            raise e
        finally:
            if op != 'read':
                logger.debug('<- %s %s', op, repr(ret))
            else:
                logger.debug('<- %s (length %d) %r', op, len(ret), ret[:16])

    def _getPath(self, path):
        """
        Given a fuse path, return the associated resource.

        :param path: path within the fuse.
        :returns: a Girder resource dictionary.
        """
        # If asked about a file in top level directory or the top directory,
        # return that it doesn't exist.  Other methods should handle '',
        # '/user', and 'collection' before calling this method.
        if '/' not in path.rstrip('/')[1:]:
            raise fuse.FuseOSError(errno.ENOENT)
        try:
            # We can't filter the resource, since that removes files'
            # assetstore information and users' size information.
            resource = path_util.lookUpPath(
                path.rstrip('/'), filter=False, force=True)
        except (path_util.NotFoundException, AccessException):
            raise fuse.FuseOSError(errno.ENOENT)
        except ValidationException:
            raise fuse.FuseOSError(errno.EROFS)
        except Exception:
            logger.exception('ServerFuse server internal error')
            raise fuse.FuseOSError(errno.EROFS)
        return resource   # {model, document}

    def _stat(self, doc, model):
        """
        Generate stat results for a resource.

        :param doc: the girder resource document.
        :param model: the girder model.
        :returns: the stat dictionary.
        """
        attr = self._defaultStat.copy()
        # We could specify distinct ino.  For instance, we could generate them
        # via a hash of the document ID (something like  int(hashlib.sha512(
        # str(doc['_id'])).hexdigest()[-8:], 16) ).  There doesn't seem to be
        # any measurable benefit of this, however, so we specify use_ino false
        # in the mount and set the value to -1 here.
        attr['st_ino'] = -1
        attr['st_nlink'] = 1
        if 'updated' in doc:
            attr['st_mtime'] = int(time.mktime(doc['updated'].timetuple()) * 1e9)
        elif 'created' in doc:
            attr['st_mtime'] = int(time.mktime(doc['created'].timetuple()) * 1e9)
        attr['st_ctime'] = attr['st_mtime']

        if model == 'file':
            attr['st_mode'] = 0o400 | stat.S_IFREG
            attr['st_size'] = doc.get('size', len(doc.get('linkUrl', '')))
        else:
            attr['st_mode'] = 0o500 | stat.S_IFDIR
            # Directories have zero size.  We could, instead, list the size
            # of all of their children via doc.get('size', 0), but that isn't
            # how most directories are reported.
            attr['st_size'] = 0
        return attr

    def _name(self, doc, model):
        """
        Return the name associated with a Girder resource.

        :param doc: the girder resource document.
        :param model: the girder model.
        :returns: the resource name as a text string.
        """
        name = path_util.getResourceName(model, doc)
        if isinstance(name, six.binary_type):
            name = name.decode('utf8')
        return name

    def _list(self, doc, model):
        """
        List the entries in a Girder user, collection, folder, or item.

        :param doc: the girder resource document.
        :param model: the girder model.
        :returns: a list of the names of resources within the specified
        document.
        """
        entries = []
        if model in ('collection', 'user', 'folder'):
            folderList = Folder().find({
                'parentId': doc['_id'],
                'parentCollection': model.lower()
            })
            for folder in folderList:
                entries.append(self._name(folder, 'folder'))
        if model == 'folder':
            for item in Folder().childItems(doc):
                entries.append(self._name(item, 'item'))
        elif model == 'item':
            for file in Item().childFiles(doc):
                entries.append(self._name(file, 'file'))
        return entries

    # We don't handle extended attributes or ioctl.
    getxattr = None
    listxattr = None
    ioctl = None

    def access(self, path, mode):
        """
        Try to load the resource associated with a path.  If we have permission
        to do so based on the current mode, report that access is allowed.
        Otherwise, an exception is raised.

        :param path: path within the fuse.
        :param mode: either F_OK to test if the resource exists, or a bitfield
            of R_OK, W_OK, and X_OK to test if read, write, and execute
            permissions are allowed.
        :returns: 0 if access is allowed.  An exception is raised if it is
            not.
        """
        if path.rstrip('/') in ('', '/user', '/collection'):
            return super(ServerFuse, self).access(path, mode)
        # mode is either F_OK or a bitfield of R_OK, W_OK, X_OK
        return 0

    def create(self, path, mode):
        """
        This is a read-only system, so don't allow create.
        """
        raise fuse.FuseOSError(errno.EROFS)

    def flush(self, path, fh=None):
        """
        We may want to disallow flush, since this is a read-only system:
            raise fuse.FuseOSError(errno.EACCES)
        For now, always succeed.
        """
        return 0

    def getattr(self, path, fh=None):
        """
        Get the attributes dictionary of a path.

        :param path: path within the fuse.
        :param fh: an open file handle.  Ignored, since path is always
            specified.
        :returns: an attribute dictionary.
        """
        if path.rstrip('/') in ('', '/user', '/collection'):
            attr = self._defaultStat.copy()
            attr['st_mode'] = 0o500 | stat.S_IFDIR
            attr['st_size'] = 0
        else:
            resource = self._getPath(path)
            attr = self._stat(resource['document'], resource['model'])
        if attr.get('st_blksize') and attr.get('st_size'):
            attr['st_blocks'] = int(
                (attr['st_size'] + attr['st_blksize'] - 1) / attr['st_blksize'])
        return attr

    def read(self, path, size, offset, fh):
        """
        Read a block of bytes from a resource.

        :param path: path within the fuse.  Ignored, since the fh parameter
            must be valid.
        :param size: maximum number of bytes to read.  There may be less if
            this is near the end of the file.
        :param offset: the offset within the file to read.
        :param fh: an open file handle.
        :returns: a block of up to <size> bytes.
        """
        with self.openFilesLock:
            if fh not in self.openFiles:
                raise fuse.FuseOSError(errno.EBADF)
            info = self.openFiles[fh]
        with info['lock']:
            handle = info['handle']
            handle.seek(offset)
            return handle.read(size)

    def readdir(self, path, fh):
        """
        Get a list of names within a directory.

        :param path: path within the fuse.
        :param fh: an open file handle.  Ignored, since path is always
            specified.
        :returns: a list of names.  This always includes . and ..
        """
        path = path.rstrip('/')
        result = [u'.', u'..']
        if path == '':
            result.extend([u'collection', u'user'])
        elif path in ('/user', '/collection'):
            model = path[1:]
            docList = ModelImporter.model(model).find({}, sort=None)
            for doc in docList:
                result.append(self._name(doc, model))
        else:
            resource = self._getPath(path)
            result.extend(self._list(resource['document'], resource['model']))
        return result

    def open(self, path, flags):
        """
        Open a path and return a descriptor.

        :param path: path within the fuse.
        :param flags: a combination of O_* flags.  This will fail if it is not
            read only.
        :returns: a file descriptor.
        """
        resource = self._getPath(path)
        if resource['model'] != 'file':
            return super(ServerFuse, self).open(path, flags)
        if flags & (os.O_APPEND | os.O_ASYNC | os.O_CREAT | os.O_DIRECTORY
                    | os.O_EXCL | os.O_RDWR | os.O_TRUNC | os.O_WRONLY):
            raise fuse.FuseOSError(errno.EROFS)
        info = {
            'path': path,
            'handle': File().open(resource['document']),
            'lock': threading.Lock(),
        }
        with self.openFilesLock:
            fh = self.nextFH
            self.nextFH += 1
            self.openFiles[fh] = info
        return fh

    def release(self, path, fh):
        """
        Release an open file handle.

        :param path: path within the fuse.
        :param fh: an open file handle.
        :returns: a file descriptor.
        """
        with self.openFilesLock:
            if fh in self.openFiles:
                with self.openFiles[fh]['lock']:
                    if 'handle' in self.openFiles[fh]:
                        self.openFiles[fh]['handle'].close()
                        del self.openFiles[fh]['handle']
                    del self.openFiles[fh]
            else:
                return super(ServerFuse, self).release(path, fh)
        return 0

    def destroy(self, path):
        """
        Handle shutdown of the FUSE.

        :param path: always '/'.
        """
        Setting().unset(SettingKey.GIRDER_MOUNT_INFORMATION)
        events.trigger('server_fuse.destroy')
        return super(ServerFuse, self).destroy(path)


class FUSELogError(fuse.FUSE):
    def __init__(self, operations, mountpoint, *args, **kwargs):
        """
        This wraps fuse.FUSE so that errors are logged rather than raising a
        RuntimeError exception.
        """
        try:
            logger.debug('Mounting %s\n' % mountpoint)
            super(FUSELogError, self).__init__(operations, mountpoint, *args, **kwargs)
            logger.debug('Mounted %s\n' % mountpoint)
        except RuntimeError:
            logprint.error(
                'Failed to mount FUSE.  Does the mountpoint (%r) exist and is '
                'it empty?  Does the user have permission to create FUSE '
                'mounts?  It could be another FUSE mount issue, too.' % (
                    mountpoint, ))
            Setting().unset(SettingKey.GIRDER_MOUNT_INFORMATION)


def unmountServer(path, lazy=False, quiet=False):
    """
    Unmount a specified path, if possible.

    :param path: the path to unmount.
    :param lazy: True to pass the lazy flag to the unmount command.
    :returns: the return code of the unmount program (0 for success).  A
        non-zero code could mean that the unmount failed or was not needed.
    """
    # We only import these for the unmount command
    import shutil
    import subprocess
    # patch shutil.which for python < 3
    if not six.PY3:
        import shutilwhich  # noqa

    if shutil.which('fusermount'):
        cmd = ['fusermount', '-u']
        if lazy:
            cmd.append('-z')
    else:
        cmd = ['umount']
        if lazy:
            cmd.append('-l')
    cmd.append(os.path.realpath(path))
    if quiet:
        with open(getattr(os, 'devnull', '/dev/null'), 'w') as devnull:
            result = subprocess.call(cmd, stdout=devnull, stderr=devnull)
    else:
        result = subprocess.call(cmd)
    return result


@click.command(
    'mount', short_help='Mount Girder files.',
    help='Mount Girder files via a read-only FUSE.  Specify the path for the mountpoint.')
@click.argument('path', type=click.Path(exists=True))
@click.option(
    '-d', '--database', default=cherrypy.config['database']['uri'],
    show_default=True,
    help='The database URI to connect to.  If this does not include a ://, '
         'the default database will be used.')
@click.option(
    '-o', '--options', 'fuseOptions', default=None,
    help='Comma separated list of additional FUSE mount options.  '
         'ro and use_ino cannot be overridden.')
@click.option(
    '-q', '--quiet', is_flag=True, default=False,
    help='Suppress Girder startup information or unmount output.')
@click.option(
    '-u', '--umount', '--unmount', 'unmount', is_flag=True, default=False,
    help='Unmount a mounted FUSE filesystem.')
@click.option(
    '-l', '-z', '--lazy', 'lazy', is_flag=True, default=False,
    help='Lazy unmount.')
@click.option('--plugins', default=None, help='Comma separated list of plugins to import.')
def main(path, database, fuseOptions, quiet, unmount, lazy, plugins):
    if unmount or lazy:
        result = unmountServer(path, lazy, quiet)
        sys.exit(result)
    mountServer(path=path, database=database, fuseOptions=fuseOptions,
                quiet=quiet, plugins=plugins)


def mountServer(path, database=None, fuseOptions=None, quiet=False, plugins=None):
    """
    Perform the mount.

    :param path: the mount location.
    :param database: a database connection URI, if it contains '://'.
        Otherwise, the default database is used.
    :param fuseOptions: a comma-separated string of options to pass to the FUSE
        mount.  A key without a value is taken as True.  Boolean values are
        case insensitive.  For instance, 'foreground' or 'foreground=True' will
        keep this program running until the SIGTERM or unmounted.
    :param quiet: if True, suppress Girder logs.
    :param plugins: an optional list of plugins to enable.  If None, use the
        plugins that are configured.
    """
    if quiet:
        curConfig = config.getConfig()
        curConfig.setdefault('logging', {})['log_quiet'] = True
        curConfig.setdefault('logging', {})['log_level'] = 'FATAL'
        girder._attachFileLogHandlers()
    if database and '://' in database:
        cherrypy.config['database']['uri'] = database
    if plugins is not None:
        plugins = plugins.split(',')
    webroot, appconf = configureServer(plugins=plugins)
    girder._setupCache()

    opClass = ServerFuse(stat=os.stat(path))
    options = {
        # By default, we run in the background so the mount command returns
        # immediately.  If we run in the foreground, a SIGTERM will shut it
        # down
        'foreground': False,
        # Cache files if their size and timestamp haven't changed.
        # This lets the OS buffer files efficiently.
        'auto_cache': True,
        # We aren't specifying our own inos
        'use_ino': False,
        # read-only file system
        'ro': True,
    }
    if sys.platform != 'darwin':
        # Automatically unmount when we try to mount again
        options['auto_unmount'] = True
    if fuseOptions:
        for opt in fuseOptions.split(','):
            if '=' in opt:
                key, value = opt.split('=', 1)
                value = (False if value.lower() == 'false' else
                         True if value.lower() == 'true' else value)
            else:
                key, value = opt, True
            if key in ('use_ino', 'ro', 'rw') and options.get(key) != value:
                logprint.warning('Ignoring the %s=%r option' % (key, value))
                continue
            options[key] = value
    Setting().set(SettingKey.GIRDER_MOUNT_INFORMATION,
                  {'path': path, 'mounttime': time.time()})
    FUSELogError(opClass, path, **options)


# You can add girder to the list of known filesystem types in linux.  For
# instance, if you create an executable file at /sbin/mount.girder that
# contains
#   #!/usr/bin/env bash
#   sudo -u <user that runs girder> girder mount -d "$@"
# then the command
#   mount -t girder <database uri> <path> -o <options>
# will work.  If you specify a string that doesn't contain :// as the database
# uri, then it will use the default girder configuration (e.g., use
# "mount -t girder girder <path>").
# If you have girder installed in a virtualenv, ifrequently prepending the
# virtualenv's bin directory to the path is enough to use it, so the
# mount.girder file becomes
#   #!/usr/bin/env bash
#   sudo -u <user that runs girder> bash -c 'PATH="<virtualenv
#       path>:$PATH" ${0} ${1+"$@"}' girder mount -d "$@"
