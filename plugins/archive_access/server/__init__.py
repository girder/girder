#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cherrypy
import os
import tarfile
import zipfile

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute, describeRoute
from girder.api.rest import boundHandler, setResponseHeader, setContentDisposition
from girder.constants import AccessType, TokenScope
from girder.exceptions import GirderException
from girder.models.file import File
from girder.utility.abstract_assetstore_adapter import FileHandle


def _fileOpen(fileModel, file):
    """
    Open a file using the local file path if possible, since that will be more
    efficient than opening it through some assetstores.

    :param fileModel: the Girder file model instance.
    :param file: file document.
    :return: A file-like object containing the bytes of the file.
    """
    try:
        return open(fileModel.getLocalFilePath(file))
    except Exception:
        return fileModel.open(file)


class ArchiveFileHandle(FileHandle):
    """
    This is a file-like API for archive files.

    These file handles are stateful, and therefore not safe for concurrent
    access. If used by multiple threads, mutexes should be used.

    :param fileModel: the Girder file model instance.
    :type fileModel: girder.model.file.File
    :param file: The girder file document.
    :type file: dict
    :param path: the path within the archive.
    :type path: str
    """
    def __init__(self, fileModel, file, path):
        super(ArchiveFileHandle, self).__init__(file, None)
        self._fileModel = fileModel
        self._path = path
        self._pos = 0
        self._open()

    def _open(self):
        """
        Open or reopen a path within archive file and populate the info
        dictionary.  The caller must reset the _pos value.  This tries to open
        the file as both a zip and a tar file, prioritizing them based on the
        file extension.
        """
        order = ('zip', 'tar') if 'zip' in self._file['exts'] else ('tar', 'zip')
        for archiveType in order:
            if archiveType == 'tar':
                try:
                    # if opened with mode 'r:' then this wouldn't read
                    # compressed tarfiles.
                    tf = tarfile.TarFile.open(fileobj=_fileOpen(self._fileModel, self._file))
                    info = tf.getmember(self._path)
                    self._info = {
                        'name': info.name,
                        'size': info.size,
                        'time': info.mtime,
                    }
                    self._fileobj = tf.extractfile(self._path)
                    return
                except tarfile.ReadError:
                    pass
            if archiveType == 'zip':
                try:
                    zf = zipfile.ZipFile(_fileOpen(self._fileModel, self._file))
                    info = zf.getinfo(self._path)
                    self._info = {
                        'name': info.filename,
                        'size': info.file_size,
                        'time': info.date_time,  # coerce to something else
                    }
                    self._fileobj = zf.open(self._path)
                    return
                except zipfile.BadZipfile:
                    pass
        raise GirderException('Not an archive file')

    def info(self):
        """
        Return some standardized information about this file.

        :returns: A dictionary with the `name` of the archive entry and the
            uncompressed `size` in bytes.
        """
        return self._info

    def read(self, size=None):
        """
        Read *size* bytes from the file data.

        :param size: The number of bytes to read from the current position. The
            actual number returned could be less than this if the end of the
            file is reached. An empty response indicates that the file has been
            completely consumed.  If None or negative, read to the end of the
            file.
        :type size: int
        :rtype: bytes
        """
        if size is None or size < 0:
            size = self._info['size'] - self._pos
        if size > self._maximumReadSize:
            raise GirderException('Read exceeds maximum allowed size.')
        data = self._fileobj.read(size)
        self._pos += len(data)
        return data

    def seek(self, offset, whence=os.SEEK_SET):
        oldPos = self._pos or 0

        if whence == os.SEEK_SET:
            self._pos = offset
        elif whence == os.SEEK_CUR:
            self._pos += offset
        elif whence == os.SEEK_END:
            self._pos = max(self._info['size'] + offset, 0)

        if self._pos != oldPos:
            if self._pos < oldPos:
                self._open()
                oldPos = 0
            pos = oldPos
            while pos < self._pos:
                chunk = min(65536, self._pos - pos)
                self._fileobj.read(chunk)
                pos += chunk


def archiveList(self, file):
    """
    This gets added to the File model to enumerate the elements of an archive
    file.  This tries to open the file as both a zip and a tar file,
    prioritizing the order based on extension.

    :param file: the file document.
    :returns: a list of paths within the archive file.
    """
    order = ('zip', 'tar') if 'zip' in file['exts'] else ('tar', 'zip')
    result = {
        'archive': False
    }
    for archiveType in order:
        if archiveType == 'tar':
            try:
                result['names'] = tarfile.TarFile.open(fileobj=_fileOpen(self, file)).getnames()
                result['archive'] = 'tar'
            except tarfile.ReadError:
                pass
        if archiveType == 'zip':
            try:
                result['names'] = [
                    name for name in zipfile.ZipFile(_fileOpen(self, file)).namelist()
                    if not name.endswith('/')]
                result['archive'] = 'zip'
            except zipfile.BadZipfile:
                pass
        if result.get('names'):
            break
    return result


def archiveOpen(self, file, path):
    """
    This gets added to the File model to open a path within an archive file.

    :param file: the file document.
    :param path: the path within the archive file.
    :returns: a file-like object that can be used as a context or handle.
    """
    return ArchiveFileHandle(self, file, path)


@boundHandler()
@access.cookie
@access.public(scope=TokenScope.DATA_READ)
@autoDescribeRoute(
    Description('Download a file from an archive file.')
    .notes('This endpoint also accepts the HTTP "Range" header for partial '
           'file downloads.')
    .modelParam('id', model=File, level=AccessType.READ)
    .param('path', 'The path within the archive.', required=True)
    .param('offset', 'Start downloading at this offset in bytes within '
           'the file.', dataType='integer', required=False, default=0)
    .param('endByte', 'If you only wish to download part of the file, '
           'pass this as the index of the last byte to download. Unlike '
           'the HTTP Range header, the endByte parameter is non-inclusive, '
           'so you should set it to the index of the byte one past the '
           'final byte you wish to receive.', dataType='integer',
           required=False)
    .param('contentDisposition', 'Specify the Content-Disposition response '
           'header disposition-type value.', required=False,
           enum=['inline', 'attachment'], default='attachment')
    .param('extraParameters', 'Arbitrary data to send along with the download request.',
           required=False)
    .errorResponse('ID was invalid.')
    .errorResponse('Read access was denied on the parent folder.', 403)
)
def downloadArchiveFile(self, file, path, offset, endByte, contentDisposition, extraParameters):
    """
    Requires read permission on the folder that contains the file's item.
    """
    with ArchiveFileHandle(File(), file, path) as fileobj:
        info = fileobj.info()
        rangeHeader = cherrypy.lib.httputil.get_ranges(
            cherrypy.request.headers.get('Range'), info['size'])
        # The HTTP Range header takes precedence over query params
        if rangeHeader and len(rangeHeader):
            # Currently we only support a single range.
            offset, endByte = rangeHeader[0]
        if offset:
            fileobj.seek(offset)
        else:
            offset = 0
        if endByte is None or endByte > info['size']:
            endByte = info['size']
        setResponseHeader('Accept-Ranges', 'bytes')
        setResponseHeader('Content-Type', 'application/octet-stream')
        setContentDisposition(os.path.basename(path), contentDisposition or 'attachment')
        setResponseHeader('Content-Length', max(endByte - offset, 0))

        if (offset or endByte < file['size']) and file['size']:
            setResponseHeader(
                'Content-Range',
                'bytes %d-%d/%d' % (offset, endByte - 1, file['size']))

        def downloadGenerator():
            pos = offset
            while pos < endByte:
                data = fileobj.read(min(65536, endByte - pos))
                yield data
                pos += len(data)
                if pos >= endByte:
                    break

        return downloadGenerator


@boundHandler()
@access.cookie
@access.public(scope=TokenScope.DATA_READ)
@describeRoute(
    Description('Download a file from an archive file.')
    .param('id', 'The ID of the file.', paramType='path')
    .param('path', 'The path within the archive.', required=True)
    .param('name', 'The name of the file.  This is ignored.',
           paramType='path')
    .param('offset', 'Start downloading at this offset in bytes within '
           'the file.', dataType='integer', required=False)
    .notes('The name parameter doesn\'t alter the download.  Some '
           'download clients save files based on the last part of a path, '
           'and specifying the name satisfies those clients.')
    .errorResponse('ID was invalid.')
    .errorResponse('Read access was denied on the parent folder.', 403)
)
def downloadArchiveFileWithName(self, id, path, name, params):
    return self.downloadArchiveFile(id=id, path=path, params=params)


@boundHandler()
@access.public(scope=TokenScope.DATA_READ)
@autoDescribeRoute(
    Description('Get a list of files within an archive file.')
    .modelParam('id', model=File, level=AccessType.READ)
    .errorResponse('ID was invalid.')
    .errorResponse('Read access was denied on the parent folder.', 403)
)
def getArchiveList(self, file):
    """
    Requires read permission on the folder that contains the file's item.
    """
    return File().archiveList(file)


def load(info):
    """
    Load the plugin into Girder.

    :param info: a dictionary of plugin information.  The name key contains the
                 name of the plugin according to Girder.
    """
    File.archiveList = archiveList
    File.archiveOpen = archiveOpen

    route = info['apiRoot'].file
    route.route('GET', (':id', 'archive'), getArchiveList)
    route.route('GET', (':id', 'archive', 'download'), downloadArchiveFile)
    route.route('GET', (':id', 'archive', 'download', ':name'), downloadArchiveFileWithName)
