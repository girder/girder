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

from ..constants import SettingKey
from .model_importer import ModelImporter
from ..models.model_base import ValidationException


class AbstractAssetstoreAdapter(object):
    """
    This defines the interface to be used by all assetstore adapters.
    """

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
        }  # pragma: no cover

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
        raise Exception('Must override processChunk in %s.'
                        % self.__class__.__name__)  # pragma: no cover

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
        raise Exception('Must override deleteFile in %s.'
                        % self.__class__.__name__)  # pragma: no cover

    def downloadFile(self, file, offset=0, headers=True):
        """
        This method is in charge of returning a value to the RESTful endpoint
        that can be used to download the file. This can return a generator
        function that streams the file directly, or can modify the cherrypy
        request headers and perform a redirect and return None, for example.
        :param file: The file document being downloaded.
        :type file: dict
        :param offset: Offset in bytes to start the download at.
        :type offset: int
        :param headers: Flag for whether headers should be sent on the response.
        :type headers: bool
        """
        raise Exception('Must override downloadFile in %s.'
                        % self.__class__.__name__)  # pragma: no cover

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
        chunkSize = None
        if hasattr(chunk, "fileno"):
            chunkSize = os.fstat(chunk.fileno()).st_size
        elif isinstance(chunk, basestring):
            chunkSize = len(chunk)
        return chunkSize

    def checkUploadSize(self, upload, chunkSize):
        """Check if the upload is valid based on the chunk size.  If this
        raises an exception, then the caller should clean up and reraise the
        exception.
        :param upload: the dictionary of upload information.  The received and
                       size values are used.
        :param chunkSize: the chunk size that needs to be validated.
        :type chunkSize: a non-negative integer or None if unknown."""
        if 'received' not in upload or 'size' not in upload:
            return
        if chunkSize is None:
            return
        if upload['received']+chunkSize > upload['size']:
            raise ValidationException('Received too many bytes.')
        if upload['received']+chunkSize != upload['size'] and \
                chunkSize < ModelImporter().model('setting').get(
                SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE):
            raise ValidationException('Chunk is smaller than the minimum size.')

    def cancelUpload(self, upload):
        """
        This is called when an upload has been begun and it should be
        abandoned.  It must clean up temporary files, chunks, or whatever other
        information the assest store contains.
        """
        raise Exception('Must override cancelUpload in %s.'
                        % self.__class__.__name__)  # pragma: no cover

    def untrackedUploads(self, knownUploads=[], delete=False):
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
        return []
