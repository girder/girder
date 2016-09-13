###############################################################################
#  Copyright 2013 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import os
import re
import six

from girder.api.rest import setResponseHeader
from girder.constants import SettingKey
from girder.models.model_base import ValidationException
from girder.utility import progress
from .model_importer import ModelImporter


class AbstractAssetstoreAdapter(ModelImporter):
    """
    This defines the interface to be used by all assetstore adapters.
    """
    def __init__(self, assetstore):
        self.assetstore = assetstore

    @staticmethod
    def validateInfo(doc):
        """
        Adapters may implement this if they need to perform any validation
        steps whenever the assetstore info is saved to the database. It should
        return the document with any necessary alterations in the success case,
        or throw an exception if validation fails.
        """
        return doc

    @staticmethod
    def fileIndexFields():
        """
        Default behavior is that no additional file fields need to be indexed
        within the database.
        """
        return []

    def capacityInfo(self):
        """
        Assetstore types that are able to report how much free and/or total
        capacity they have should override this method. Default behavior is to
        report both quantities as unknown.

        :returns: A dict with 'free' and 'total' keys whose values are
                  either bytes (ints) or None for an unknown quantity.
        """
        return {
            'free': None,
            'total': None
        }

    def initUpload(self, upload):
        """
        This must be called before any chunks are uploaded to do any
        additional behavior and optionally augment the upload document. The
        method must return the upload document. Default behavior is to
        simply return the upload document unmodified.

        :param upload: The upload document to optionally augment.
        :type upload: dict
        """
        return upload  # pragma: no cover

    def uploadChunk(self, upload, chunk):
        """
        Call this method to process each chunk of an upload.

        :param upload: The upload document to update.
        :type upload: dict
        :param chunk: The file object representing the chunk that was uploaded.
        :type chunk: file
        :returns: Must return the upload document with any optional changes.
        """
        raise NotImplementedError('Must override processChunk in %s.' %
                                  self.__class__.__name__)  # pragma: no cover

    def finalizeUpload(self, upload, file):
        """
        Call this once the last chunk has been processed. This method does not
        need to delete the upload document as that will be deleted by the
        caller afterward. This method may augment the File document, and must
        return the File document.

        :param upload: The upload document.
        :type upload: dict
        :param file: The file document that was created.
        :type file: dict
        :returns: The file document with optional modifications.
        """
        return file

    def requestOffset(self, upload):
        """
        Request the offset for resuming an interrupted upload. Default behavior
        simply returns the 'received' field of the upload document. This method
        exists because in some cases, such as when the server crashes, it's
        possible that the received field is not accurate, so adapters may
        implement this to provide the actual next byte required.
        """
        return upload['received']

    def deleteFile(self, file):
        """
        This is called when a File is deleted to allow the adapter to remove
        the data from within the assetstore. This method should not modify
        or delete the file object, as the caller will delete it afterward.

        :param file: The File document about to be deleted.
        :type file: dict
        """
        raise NotImplementedError('Must override deleteFile in %s.' %
                                  self.__class__.__name__)  # pragma: no cover

    def shouldImportFile(self, path, params):
        """
        This is a helper used during the import process to determine if a file located at
        the specified path should be imported, based on the request parameters. Exclusion
        takes precedence over inclusion.

        :param path: The path of the file.
        :type path: str
        :param params: The request parameters.
        :type params: dict
        :rtype: bool
        """
        include = params.get('fileIncludeRegex')
        exclude = params.get('fileExcludeRegex')

        fname = os.path.basename(path)

        if exclude and re.match(exclude, fname):
            return False

        if include:
            return re.match(include, fname)

        return True

    def downloadFile(self, file, offset=0, headers=True, endByte=None,
                     contentDisposition=None, extraParameters=None, **kwargs):
        """
        This method is in charge of returning a value to the RESTful endpoint
        that can be used to download the file. This can return a generator
        function that streams the file directly, or can modify the response
        headers and perform a redirect and return None, for example.

        :param file: The file document being downloaded.
        :type file: dict
        :param offset: Offset in bytes to start the download at.
        :type offset: int
        :param headers: Flag for whether headers should be sent on the response.
        :type headers: bool
        :param endByte: Final byte to download. If ``None``, downloads to the
            end of the file.
        :type endByte: int or None
        :param contentDisposition: Value for Content-Disposition response
            header disposition-type value.
        :type contentDisposition: str or None
        :type extraParameters: str or None
        """
        raise NotImplementedError('Must override downloadFile in %s.' %
                                  self.__class__.__name__)  # pragma: no cover

    def findInvalidFiles(self, progress=progress.noProgress, filters=None,
                         checkSize=True, **kwargs):
        """
        Finds and yields any invalid files in the assetstore. It is left to
        the caller to decide what to do with them.

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
        raise NotImplementedError('Must override findInvalidFiles in %s.' %
                                  self.__class__.__name__)  # pragma: no cover

    def copyFile(self, srcFile, destFile):
        """
        This method copies the necessary fields and data so that the
        destination file contains the same data as the source file.

        :param srcFile: The original File document.
        :type srcFile: dict
        :param destFile: The File which should have the data copied to it.
        :type destFile: dict
        :returns: A dict with the destination file.
        """
        return destFile

    def getChunkSize(self, chunk):
        """
        Given a chunk that is either a file-like object or a string, attempt to
        determine its length.  If it is a file-like object, then this relies on
        being able to use fstat.

        :param chunk: the chunk to get the size of
        :type chunk: a file-like object or a string
        :returns: the length of the chunk if known, or None.
        """
        if isinstance(chunk, six.BytesIO):
            return
        elif hasattr(chunk, "fileno"):
            return os.fstat(chunk.fileno()).st_size
        elif isinstance(chunk, six.text_type):
            return len(chunk.encode('utf8'))
        else:
            return len(chunk)

    def setContentHeaders(self, file, offset, endByte, contentDisposition=None):
        """
        Sets the Content-Length, Content-Disposition, Content-Type, and also
        the Content-Range header if this is a partial download.

        :param file: The file being downloaded.
        :param offset: The start byte of the download.
        :type offset: int
        :param endByte: The end byte of the download (non-inclusive).
        :type endByte: int
        :param contentDisposition: Content-Disposition response header
            disposition-type value, if None, Content-Disposition will
            be set to 'attachment; filename=$filename'.
        :type contentDisposition: str or None
        """
        setResponseHeader(
            'Content-Type',
            file.get('mimeType') or 'application/octet-stream')
        if contentDisposition == 'inline':
            setResponseHeader(
                'Content-Disposition',
                'inline; filename="%s"' % file['name'])
        else:
            setResponseHeader(
                'Content-Disposition',
                'attachment; filename="%s"' % file['name'])
        setResponseHeader('Content-Length', max(endByte - offset, 0))

        if (offset or endByte < file['size']) and file['size']:
            setResponseHeader(
                'Content-Range',
                'bytes %d-%d/%d' % (offset, endByte - 1, file['size']))

    def checkUploadSize(self, upload, chunkSize):
        """
        Check if the upload is valid based on the chunk size.  If this
        raises an exception, then the caller should clean up and reraise the
        exception.

        :param upload: the dictionary of upload information.  The received and
                       size values are used.
        :param chunkSize: the chunk size that needs to be validated.
        :type chunkSize: a non-negative integer or None if unknown.
        """
        if 'received' not in upload or 'size' not in upload:
            return
        if chunkSize is None:
            return
        if upload['received'] + chunkSize > upload['size']:
            raise ValidationException('Received too many bytes.')
        if upload['received'] + chunkSize != upload['size'] and \
                chunkSize < self.model('setting').get(
                SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE):
            raise ValidationException('Chunk is smaller than the minimum size.')

    def cancelUpload(self, upload):
        """
        This is called when an upload has been begun and it should be
        abandoned.  It must clean up temporary files, chunks, or whatever other
        information the assetstore contains.
        """
        raise NotImplementedError('Must override cancelUpload in %s.' %
                                  self.__class__.__name__)  # pragma: no cover

    def untrackedUploads(self, knownUploads=(), delete=False):
        """
        List and optionally discard uploads that are in the assetstore but not
        in the known list.

        :param knownUploads: a list of upload dictionaries of all known
                             incomplete uploads.
        :type knownUploads: list
        :param delete: if True, delete any unknown uploads.
        :type delete: bool
        :returns: a list of unknown uploads.
        """
        return ()

    def importData(self, parent, parentType, params, progress, user, **kwargs):
        """
        Assetstores that are capable of importing pre-existing data from the
        underlying storage medium can implement this method.

        :param parent: The parent object to import into.
        :param parentType: The model type of the parent object (folder, user,
            or collection).
        :type parentType: str
        :param params: Additional parameters required for the import process.
            Typically includes an importPath field representing a root path
            on the underlying storage medium.
        :type params: dict
        :param progress: Object on which to record progress if possible.
        :type progress: :py:class:`girder.utility.progress.ProgressContext`
        :param user: The Girder user performing the import.
        :type user: dict or None
        """
        raise NotImplementedError(
            'The %s assetstore type does not support importing existing data.'
            % self.__class__.__name__)  # pragma: no cover

    def fileUpdated(self, file):
        """
        This is called when the file document has been changed. Any assetstore
        implementation that needs to do anything when the file document changes
        should override this method.

        :param file: The updated file document.
        :type file: dict
        """
        pass
