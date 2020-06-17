# -*- coding: utf-8 -*-
import filelock
from hashlib import sha512
import io
import os
import psutil
import shutil
import stat
import tempfile

from girder import events, logger
from girder.api.rest import setResponseHeader
from girder.exceptions import ValidationException, GirderException
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.upload import Upload
from girder.utility import mkdir, progress
from . import _hash_state
from .abstract_assetstore_adapter import AbstractAssetstoreAdapter

BUF_SIZE = 65536

# Default permissions for the files written to the filesystem
DEFAULT_PERMS = stat.S_IRUSR | stat.S_IWUSR


class FilesystemAssetstoreAdapter(AbstractAssetstoreAdapter):
    """
    This assetstore type stores files on the filesystem underneath a root
    directory. Files are named by their SHA-512 hash, which avoids duplication
    of file content.

    :param assetstore: The assetstore to act on.
    :type assetstore: dict
    """

    @staticmethod
    def validateInfo(doc):
        """
        Makes sure the root field is a valid absolute path and is writeable.
        It also conveniently update the root field replacing the initial
        component by the user home directory running the server if it matches
        ``~`` or ``~user``.
        """
        doc['root'] = os.path.expanduser(doc['root'])

        if not os.path.isabs(doc['root']):
            raise ValidationException('You must provide an absolute path '
                                      'for the root directory.', 'root')

        try:
            mkdir(doc['root'])
        except OSError:
            msg = 'Could not make directory "%s".' % doc['root']
            logger.exception(msg)
            raise ValidationException(msg)
        if not os.access(doc['root'], os.W_OK):
            raise ValidationException(
                'Unable to write into directory "%s".' % doc['root'])

        if not doc.get('perms'):
            doc['perms'] = DEFAULT_PERMS
        else:
            try:
                perms = doc['perms']
                if not isinstance(perms, int):
                    perms = int(doc['perms'], 8)

                # Make sure that mode is still rw for user
                if not perms & stat.S_IRUSR or not perms & stat.S_IWUSR:
                    raise ValidationException(
                        'File permissions must allow "rw" for user.')
                doc['perms'] = perms
            except ValueError:
                raise ValidationException(
                    'File permissions must be an octal integer.')

    @staticmethod
    def fileIndexFields():
        """
        File documents should have an index on their sha512 field, as well as
        whether or not they are imported.
        """
        return ['sha512', 'imported']

    def __init__(self, assetstore):
        super().__init__(assetstore)
        # If we can't create the temp directory, the assetstore still needs to
        # be initialized so that it can be deleted or modified.  The validation
        # prevents invalid new assetstores from being created, so this only
        # happens to existing assetstores that no longer can access their temp
        # directories.
        self.tempDir = os.path.join(self.assetstore['root'], 'temp')
        try:
            mkdir(self.tempDir)
        except OSError:
            self.unavailable = True
            logger.exception('Failed to create filesystem assetstore '
                             'directories %s' % self.tempDir)
        if not os.access(self.assetstore['root'], os.W_OK):
            self.unavailable = True
            logger.error('Could not write to assetstore root: %s',
                         self.assetstore['root'])

    def capacityInfo(self):
        """
        For filesystem assetstores, we just need to report the free and total
        space on the filesystem where the assetstore lives.
        """
        try:
            usage = psutil.disk_usage(self.assetstore['root'])
            return {'free': usage.free, 'total': usage.total}
        except OSError:
            logger.exception(
                'Failed to get disk usage of %s' % self.assetstore['root'])
        # If psutil.disk_usage fails or we can't query the assetstore's root
        # directory, just report nothing regarding disk capacity
        return {
            'free': None,
            'total': None
        }

    def initUpload(self, upload):
        """
        Generates a temporary file and sets its location in the upload document
        as tempFile. This is the file that the chunks will be appended to.
        """
        fd, path = tempfile.mkstemp(dir=self.tempDir)
        os.close(fd)  # Must close this file descriptor or it will leak
        upload['tempFile'] = path
        upload['sha512state'] = _hash_state.serializeHex(sha512())
        return upload

    def uploadChunk(self, upload, chunk):
        """
        Appends the chunk into the temporary file.
        """
        # If we know the chunk size is too large or small, fail early.
        self.checkUploadSize(upload, self.getChunkSize(chunk))

        if isinstance(chunk, str):
            chunk = chunk.encode('utf8')

        if isinstance(chunk, bytes):
            chunk = io.BytesIO(chunk)

        # Restore the internal state of the streaming SHA-512 checksum
        checksum = _hash_state.restoreHex(upload['sha512state'], 'sha512')

        if self.requestOffset(upload) > upload['received']:
            # This probably means the server died midway through writing last
            # chunk to disk, and the database record was not updated. This
            # means we need to update the sha512 state with the difference.
            with open(upload['tempFile'], 'rb') as tempFile:
                tempFile.seek(upload['received'])
                while True:
                    data = tempFile.read(BUF_SIZE)
                    if not data:
                        break
                    checksum.update(data)

        with open(upload['tempFile'], 'a+b') as tempFile:
            size = 0
            while not upload['received'] + size > upload['size']:
                data = chunk.read(BUF_SIZE)
                if not data:
                    break
                size += len(data)
                tempFile.write(data)
                checksum.update(data)
        chunk.close()

        try:
            self.checkUploadSize(upload, size)
        except ValidationException:
            with open(upload['tempFile'], 'a+b') as tempFile:
                tempFile.truncate(upload['received'])
            raise

        # Persist the internal state of the checksum
        upload['sha512state'] = _hash_state.serializeHex(checksum)
        upload['received'] += size
        return upload

    def requestOffset(self, upload):
        """
        Returns the size of the temp file.
        """
        return os.stat(upload['tempFile']).st_size

    def finalizeUpload(self, upload, file):
        """
        Moves the file into its permanent content-addressed location within the
        assetstore. Directory hierarchy yields 256^2 buckets.
        """
        hash = _hash_state.restoreHex(upload['sha512state'], 'sha512').hexdigest()
        dir = os.path.join(hash[0:2], hash[2:4])
        absdir = os.path.join(self.assetstore['root'], dir)

        path = os.path.join(dir, hash)
        abspath = os.path.join(self.assetstore['root'], path)

        # Store the hash in the upload so that deleting a file won't delete
        # this file
        if '_id' in upload:
            upload['sha512'] = hash
            Upload().update({'_id': upload['_id']}, update={'$set': {'sha512': hash}})

        mkdir(absdir)

        # Only maintain the lock which checking if the file exists.  The only
        # other place the lock is used is checking if an upload task has
        # reserved the file, so this is sufficient.
        with filelock.FileLock(abspath + '.deleteLock'):
            pathExists = os.path.exists(abspath)
        if pathExists:
            # Already have this file stored, just delete temp file.
            os.unlink(upload['tempFile'])
        else:
            # Move the temp file to permanent location in the assetstore.
            # shutil.move works across filesystems
            shutil.move(upload['tempFile'], abspath)
            try:
                os.chmod(abspath, self.assetstore.get('perms', DEFAULT_PERMS))
            except OSError:
                # some filesystems may not support POSIX permissions
                pass

        file['sha512'] = hash
        file['path'] = path

        return file

    def fullPath(self, file):
        """
        Utility method for constructing the full (absolute) path to the given
        file.
        """
        if file.get('imported'):
            return file['path']
        else:
            return os.path.join(self.assetstore['root'], file['path'])

    def downloadFile(self, file, offset=0, headers=True, endByte=None,
                     contentDisposition=None, extraParameters=None, **kwargs):
        """
        Returns a generator function that will be used to stream the file from
        disk to the response.
        """
        if endByte is None or endByte > file['size']:
            endByte = file['size']

        path = self.fullPath(file)

        if not os.path.isfile(path):
            raise GirderException(
                'File %s does not exist.' % path,
                'girder.utility.filesystem_assetstore_adapter.'
                'file-does-not-exist')

        if headers:
            setResponseHeader('Accept-Ranges', 'bytes')
            self.setContentHeaders(file, offset, endByte, contentDisposition)

        def stream():
            bytesRead = offset
            with open(path, 'rb') as f:
                if offset > 0:
                    f.seek(offset)

                while True:
                    readLen = min(BUF_SIZE, endByte - bytesRead)
                    if readLen <= 0:
                        break

                    data = f.read(readLen)
                    bytesRead += readLen

                    if not data:
                        break
                    yield data

        return stream

    def deleteFile(self, file):
        """
        Deletes the file from disk if it is the only File in this assetstore
        with the given sha512. Imported files are not actually deleted.
        """
        from girder.models.file import File

        if file.get('imported') or 'path' not in file:
            return

        q = {
            'sha512': file['sha512'],
            'assetstoreId': self.assetstore['_id']
        }
        path = os.path.join(self.assetstore['root'], file['path'])
        if os.path.isfile(path):
            with filelock.FileLock(path + '.deleteLock'):
                matching = File().find(q, limit=2, fields=[])
                matchingUpload = Upload().findOne(q)
                if matching.count(True) == 1 and matchingUpload is None:
                    try:
                        os.unlink(path)
                    except Exception:
                        logger.exception('Failed to delete file %s' % path)

    def cancelUpload(self, upload):
        """
        Delete the temporary files associated with a given upload.
        """
        if os.path.exists(upload['tempFile']):
            os.unlink(upload['tempFile'])

    def importFile(self, item, path, user, name=None, mimeType=None, **kwargs):
        """
        Import a single file from the filesystem into the assetstore.

        :param item: The parent item for the file.
        :type item: dict
        :param path: The path on the local filesystem.
        :type path: str
        :param user: The user to list as the creator of the file.
        :type user: dict
        :param name: Name for the file. Defaults to the basename of ``path``.
        :type name: str
        :param mimeType: MIME type of the file if known.
        :type mimeType: str
        :returns: The file document that was created.
        """
        logger.debug('Importing file %s to item %s on filesystem assetstore %s',
                     path, item['_id'], self.assetstore['_id'])
        stat = os.stat(path)
        name = name or os.path.basename(path)

        file = File().createFile(
            name=name, creator=user, item=item, reuseExisting=True, assetstore=self.assetstore,
            mimeType=mimeType, size=stat.st_size, saveFile=False)
        file['path'] = os.path.abspath(os.path.expanduser(path))
        file['mtime'] = stat.st_mtime
        file['imported'] = True
        file = File().save(file)
        logger.debug('Imported file %s to item %s on filesystem assetstore %s',
                     path, item['_id'], self.assetstore['_id'])
        return file

    def _importDataAsItem(self, name, user, folder, path, files, reuseExisting=True, params=None):
        params = params or {}
        item = Item().createItem(
            name=name, creator=user, folder=folder, reuseExisting=reuseExisting)
        events.trigger('filesystem_assetstore_imported',
                       {'id': item['_id'], 'type': 'item',
                        'importPath': path})
        for fname in files:
            fpath = os.path.join(path, fname)
            if self.shouldImportFile(fpath, params):
                self.importFile(item, fpath, user, name=fname)

    def _hasOnlyFiles(self, path, files):
        return all(os.path.isfile(os.path.join(path, name)) for name in files)

    def _importFileToFolder(self, name, user, parent, parentType, path):
        if parentType != 'folder':
            raise ValidationException(
                'Files cannot be imported directly underneath a %s.' % parentType)

        item = Item().createItem(name=name, creator=user, folder=parent, reuseExisting=True)
        events.trigger('filesystem_assetstore_imported', {
            'id': item['_id'],
            'type': 'item',
            'importPath': path
        })
        self.importFile(item, path, user, name=name)

    def importData(self, parent, parentType, params, progress, user, leafFoldersAsItems):
        importPath = params['importPath']

        if not os.path.exists(importPath):
            raise ValidationException('Not found: %s.' % importPath)
        if not os.path.isdir(importPath):
            name = os.path.basename(importPath)
            progress.update(message=name)
            self._importFileToFolder(name, user, parent, parentType, importPath)
            return

        listDir = os.listdir(importPath)

        if parentType != 'folder' and any(
                os.path.isfile(os.path.join(importPath, val)) for val in listDir):
            raise ValidationException(
                'Files cannot be imported directly underneath a %s.' % parentType)

        if leafFoldersAsItems and self._hasOnlyFiles(importPath, listDir):
            self._importDataAsItem(
                os.path.basename(importPath.rstrip(os.sep)), user, parent, importPath,
                listDir, params=params)
            return

        for name in listDir:
            progress.update(message=name)
            path = os.path.join(importPath, name)

            if os.path.isdir(path):
                localListDir = os.listdir(path)
                if leafFoldersAsItems and self._hasOnlyFiles(path, localListDir):
                    self._importDataAsItem(name, user, parent, path, localListDir, params=params)
                else:
                    folder = Folder().createFolder(
                        parent=parent, name=name, parentType=parentType,
                        creator=user, reuseExisting=True)
                    events.trigger(
                        'filesystem_assetstore_imported', {
                            'id': folder['_id'],
                            'type': 'folder',
                            'importPath': path
                        })
                    nextPath = os.path.join(importPath, name)
                    self.importData(
                        folder, 'folder', params=dict(params, importPath=nextPath),
                        progress=progress, user=user, leafFoldersAsItems=leafFoldersAsItems)
            else:
                if self.shouldImportFile(path, params):
                    self._importFileToFolder(name, user, parent, parentType, path)

    def findInvalidFiles(self, progress=progress.noProgress, filters=None,
                         checkSize=True, **kwargs):
        """
        Goes through every file in this assetstore and finds those whose
        underlying data is missing or invalid. This is a generator function --
        for each invalid file found, a dictionary is yielded to the caller that
        contains the file, its absolute path on disk, and a reason for invalid,
        e.g. "missing" or "size".

        :param progress: Pass a progress context to record progress.
        :type progress: :py:class:`girder.utility.progress.ProgressContext`
        :param filters: Additional query dictionary to restrict the search for
            files. There is no need to set the ``assetstoreId`` in the filters,
            since that is done automatically.
        :type filters: dict or None
        :param checkSize: Whether to make sure the size of the underlying
            data matches the size of the file.
        :type checkSize: bool
        """
        filters = filters or {}
        q = dict({
            'assetstoreId': self.assetstore['_id']
        }, **filters)

        cursor = File().find(q)
        progress.update(total=cursor.count(), current=0)

        for file in cursor:
            progress.update(increment=1, message=file['name'])
            path = self.fullPath(file)

            if not os.path.isfile(path):
                yield {
                    'reason': 'missing',
                    'file': file,
                    'path': path
                }
            elif checkSize and os.path.getsize(path) != file['size']:
                yield {
                    'reason': 'size',
                    'file': file,
                    'path': path
                }

    def getLocalFilePath(self, file):
        """
        Return a path to the file on the local file system.

        :param file: The file document.
        :returns: a local path to the file or None if no such path is known.
        """
        path = self.fullPath(file)
        # If an imported file has moved, don't report the path
        if path and os.path.exists(path):
            return path
        return super().getLocalFilePath(file)
