import atexit
import errno
import fuse
import os
import shutil
import six
import stat
import sys
import subprocess
import threading
import time

from girder import events, logger, logprint
from girder.constants import AccessType
from girder.exceptions import AccessException, ValidationException
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.utility.model_importer import ModelImporter
from girder.utility import path as path_util


# There can be multiple FUSE mounts, each with different user permissions.  If
# the mount needs to be exposed in some manner to something other than the
# main server, this could be used to limit which resources are visible.  Since
# the server can already access all resources, this is not of utility from
# within the server itself.
_fuseMounts = {}
_fuseMountsLock = threading.RLock()


class ServerFuse(fuse.Operations, ModelImporter):
    """
    This class handles FUSE operations that are non-default.  It exposes the
    Girder resources via the resource path in a read-only manner.  It could be
    extended to expose metadata and other resources by extending the available
    paths.  Files can also be reached via a path shortcut of /file/<id>.
    """
    # Use Girder logging by default.
    log = logger

    def __init__(self, level=AccessType.ADMIN, user=None, force=True, stat=None):
        """
        Instantiate the operations class.  This sets up tracking for open
        files and file descriptor numbers (handles).

        :param level: access level for this mount point.
        :param user: access user for this mount point.  If force is True, this
            may be None for full-access.
        :param force: if True, don't validate access permissions (level and
            user are ignored).
        :param stat: the results of an os.stat call which should be used as
            default values for files in the FUSE.  Files in the FUSE will have
            the same uid, gid, and atime.  If the resource lacks both an
            updated and a created time stamp, the ctime and mtime will also be
            taken from this.  If None, this defaults to the user of the Girder
            process's home directory,
        """
        super(ServerFuse, self).__init__()
        self.level = level
        self.user = user
        self.force = force
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
        if self.log:
            self.log.debug('-> %s %s %s', op, path, repr(args))
        ret = '[exception]'
        try:
            ret = getattr(self, op)(path, *args, **kwargs)
            return ret
        except Exception as e:
            # Log all exceptions and then reraise them
            if self.log:
                if getattr(e, 'errno', None) in (errno.ENOENT, errno.EACCES):
                    self.log.debug('-- %s %r', op, e)
                else:
                    self.log.exception('-- %s', op)
            raise e
        finally:
            if self.log:
                if op != 'read':
                    self.log.debug('<- %s %s', op, repr(ret))
                else:
                    self.log.debug('<- %s (length %d) %r', op, len(ret), ret[:16])

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
                path.rstrip('/'), filter=False, user=self.user, force=self.force)
        except (path_util.NotFoundException, AccessException):
            raise fuse.FuseOSError(errno.ENOENT)
        except ValidationException:
            raise fuse.FuseOSError(errno.EROFS)
        except Exception:
            if self.log:
                self.log.exception('ServerFuse server internal error')
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
            attr['st_mtime'] = time.mktime(doc['updated'].timetuple())
        elif 'created' in doc:
            attr['st_mtime'] = time.mktime(doc['created'].timetuple())
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
            if self.force:
                folderList = Folder().find({
                    'parentId': doc['_id'],
                    'parentCollection': model.lower()
                })
            else:
                folderList = Folder().childFolders(
                    parent=doc, parentType=model, user=self.user)
            for folder in folderList:
                entries.append(self._name(folder, 'folder'))
        if model == 'folder':
            for item in Folder().childItems(doc):
                entries.append(self._name(item, 'item'))
        elif model == 'item':
            for file in Item().childFiles(doc):
                entries.append(self._name(file, 'file'))
        return entries

    # We don't handle extended attributes.
    getxattr = None
    listxattr = None

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
        # we need to validate if the resource can be accessed
        resource = self._getPath(path)
        if mode != os.F_OK and not self.force:
            if (mode & os.R_OK):
                self.model(resource['model']).requireAccess(
                    resource['document'], self.user, level=AccessType.READ)
            if (mode & os.W_OK):
                self.model(resource['model']).requireAccess(
                    resource['document'], self.user, level=AccessType.WRITE)
            if (mode & os.X_OK):
                self.model(resource['model']).requireAccess(
                    resource['document'], self.user, level=AccessType.ADMIN)
        return 0

    def create(self, path, mode):
        """
        This is a read-only system, so don't allow create.
        """
        raise fuse.FuseOSError(errno.EROFS)

    def flush(self, path, fh=None):
        """
        We may want to disallow flush, since his is a read-only system:
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
            if self.force:
                docList = self.model(model).find({}, sort=None)
            else:
                docList = self.model(model).list(user=self.user)
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
        if flags & (os.O_APPEND | os.O_ASYNC | os.O_CREAT | os.O_DIRECTORY |
                    os.O_EXCL | os.O_RDWR | os.O_TRUNC | os.O_WRONLY):
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
        events.trigger('server_fuse.destroy')
        return super(ServerFuse, self).destroy(path)


@atexit.register
def unmountAll():
    """
    Unmount all mounted FUSE mounts.
    """
    for name in list(_fuseMounts.keys()):
        unmountServerFuse(name)


def unmountServerFuse(name):
    """
    Unmount a mounted FUSE mount.  This may fail if there are open files on the
    mount.

    :param name: a key within the list of known mounts.
    """
    with _fuseMountsLock:
        entry = _fuseMounts.pop(name, None)
        if entry:
            events.trigger('server_fuse.unmount', {'name': name})
            path = entry['path']
            # Girder uses shutilwhich on Python < 3
            if shutil.which('fusermount'):
                subprocess.call(['fusermount', '-u', os.path.realpath(path)])
            else:
                subprocess.call(['umount', os.path.realpath(path)])
            if entry['thread']:
                entry['thread'].join(10)
            # clean up previous processes so there aren't any zombies
            try:
                os.waitpid(-1, os.WNOHANG)
            except OSError:
                # Don't throw an error; sometimes we get an
                # errno 10: no child processes
                pass


class FUSELogError(fuse.FUSE):
    def __init__(self, name, onError, operations, mountpoint, *args, **kwargs):
        """
        This wraps fuse.FUSE so that errors are logged rather than raising a
        RuntimeError exception.

        :param name: key for the mount point.
        :param onError: a function that is called with `name` if initialization
            fails.
        """
        try:
            super(FUSELogError, self).__init__(operations, mountpoint, *args, **kwargs)
        except RuntimeError:
            logprint.error(
                'Failed to mount FUSE.  Does the mountpoint (%r) exist and is '
                'it empty?  Does the user have permission to create FUSE '
                'mounts?  It could be another FUSE mount issue, too.' % (
                    mountpoint, ))
            onError(name)


def handleFuseMountFailure(name):
    """
    If a FUSE mount fails to initialize inside, remove it from the list of
    mounts and clean up its thread.

    :param name: key for the mount point.
    """
    with _fuseMountsLock:
        _fuseMounts.pop(name, None)


def mountServerFuse(name, path, level=AccessType.ADMIN, user=None, force=False):
    """
    Mount a FUSE at a specific path with authorization for a given user.

    :param name: a key for this mount mount.  Each mount point must have a
        distinct key.
    :param path: the location where this mount will be in the local filesystem.
        This should be an empty directory.
    :param level: access level used when checking which resources are available
        within the FUSE.  This is ignored currently, but could be used if
        non-readonly access is ever implemented.
    :param user: the user used for authorizing resource access.
    :param force: if True, all resources are available without checking the
        user or level.
    :returns: True if successful.  'present' if the mount is already present.
        None on failure.
    """
    with _fuseMountsLock:
        if name in _fuseMounts:
            if (_fuseMounts[name]['level'] == level and
                    _fuseMounts[name]['user'] == user and
                    _fuseMounts[name]['force'] == force):
                return 'present'
            unmountServerFuse(name)
        entry = {
            'level': level,
            'user': user,
            'force': force,
            'path': path,
            'stat': dict((key, getattr(os.stat(path), key)) for key in (
                'st_atime', 'st_ctime', 'st_gid', 'st_mode', 'st_mtime',
                'st_nlink', 'st_size', 'st_uid')),
            'thread': None
        }
        try:
            # We run the file system in a thread, but as a foreground process.
            # This allows multiple mounted fuses to play well together and stop
            # when the program is stopped.
            opClass = ServerFuse(level=level, user=user, force=force,
                                 stat=os.stat(path))
            options = {
                # Running in a thread in the foreground makes it easier to
                # clean up the process when we need to shut it down.
                'foreground': True,
                # Automatically unmount when python we try to mount again
                'auto_unmount': True,
                # Cache files if their size and timestamp haven't changed.
                # This lets to OS buffer files efficiently.
                'auto_cache': True,
                # We aren't specifying our own inos
                'use_ino': False,
                # read-only file system
                'ro': True,
            }
            if sys.platform == 'darwin':
                del options['auto_unmount']
            fuseThread = threading.Thread(target=FUSELogError, args=(
                name, handleFuseMountFailure, opClass, path), kwargs=options)
            entry['thread'] = fuseThread
            _fuseMounts[name] = entry
            fuseThread.daemon = True
            fuseThread.start()
            logprint.info('Mounted %s at %s' % (name, path))
            events.trigger('server_fuse.mount', {'name': name})
            return True
        except Exception:
            logger.exception('Failed to mount %s at %s' % (name, path))


def isServerFuseMounted(name, level=AccessType.ADMIN, user=None, force=False):
    """
    Check if a named FUSE is mounted with specific authorization.

    :param name: a key for this mount mount.  Each mount point must have a
        distinct key.
    :param level: access level used when checking which resources are available
        within the FUSE.  This is ignored currently, but could be used if
        non-readonly access is ever implemented.
    :param user: the user used for authorizing resource access.
    :param force: if True, all resources are available without checking the
        user or level.
    :returns: True if mounted, False if not.
    """
    with _fuseMountsLock:
        if name in _fuseMounts:
            if (_fuseMounts[name]['level'] == level and
                    _fuseMounts[name]['user'] == user and
                    _fuseMounts[name]['force'] == force):
                return True
    return False


def getServerFusePath(name, type, doc):
    """
    Given a fuse name and a resource, return the file path.

    :param name: key used for the fuse mount.
    :param type: the resource model type.
    :param doc: the resource document.
    :return: a path to the resource.
    """
    if name not in _fuseMounts:
        return None
    return _fuseMounts[name]['path'].rstrip('/') + path_util.getResourcePath(
        type, doc, user=_fuseMounts[name]['user'], force=_fuseMounts[name]['force'])
