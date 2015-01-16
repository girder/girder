#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import cherrypy
import os
import psutil
import shutil
import stat
import tempfile

from StringIO import StringIO
from hashlib import sha512
from . import sha512_state
from .abstract_assetstore_adapter import AbstractAssetstoreAdapter
from .model_importer import ModelImporter
from girder.models.model_base import ValidationException, GirderException
from girder import logger

BUF_SIZE = 65536


class FilesystemAssetstoreAdapter(AbstractAssetstoreAdapter):
    """
    This assetstore type stores files on the filesystem underneath a root
    directory. Files are named by their SHA-512 hash, which avoids duplication
    of file content.
    """

    @staticmethod
    def validateInfo(doc):
        """
        Makes sure the root field is a valid absolute path and is writeable.
        """
        if not os.path.isabs(doc['root']):
            raise ValidationException('You must provide an absolute path '
                                      'for the root directory.', 'root')
        if not os.path.isdir(doc['root']):
            try:
                os.makedirs(doc['root'])
            except OSError:
                raise ValidationException('Could not make directory "{}".'
                                          .format(doc['root'], 'root'))
        if not os.access(doc['root'], os.W_OK):
            raise ValidationException('Unable to write into directory "{}".'
                                      .format(doc['root'], 'root'))

    @staticmethod
    def fileIndexFields():
        """
        File documents should have an index on their sha512 field.
        """
        return ['sha512']

    def __init__(self, assetstore):
        """
        :param assetstore: The assetstore to act on.
        """
        self.assetstore = assetstore
        # If we can't create the temp directory, the assetstore still needs to
        # be initialized so that it can be deleted or modified.  The validation
        # prevents invalid new assetstores from being created, so this only
        # happens to existing assetstores that no longer can access their temp
        # directories.
        self.tempDir = os.path.join(assetstore['root'], 'temp')
        if not os.path.exists(self.tempDir):
            try:
                os.makedirs(self.tempDir)
            except OSError:
                logger.exception('Failed to create filesystem assetstore '
                                 'directories {}'.format(self.tempDir))

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
        return {  # pragma: no cover
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
        upload['sha512state'] = sha512_state.serializeHex(sha512())
        return upload

    def uploadChunk(self, upload, chunk):
        """
        Appends the chunk into the temporary file.
        """
        # If we know the chunk size is too large or small, fail early.
        self.checkUploadSize(upload, self.getChunkSize(chunk))

        if isinstance(chunk, basestring):
            chunk = StringIO(chunk)

        # Restore the internal state of the streaming SHA-512 checksum
        checksum = sha512_state.restoreHex(upload['sha512state'])

        if self.requestOffset(upload) > upload['received']:
            # This probably means the server died midway through writing last
            # chunk to disk, and the database record was not updated. This means
            # we need to update the sha512 state with the difference.
            with open(upload['tempFile'], 'rb') as tempFile:
                tempFile.seek(upload['received'])
                while True:
                    data = tempFile.read(BUF_SIZE)
                    if not data:
                        break
                    checksum.update(data)

        with open(upload['tempFile'], 'a+b') as tempFile:
            size = 0
            while not upload['received']+size > upload['size']:
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
        upload['sha512state'] = sha512_state.serializeHex(checksum)
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
        hash = sha512_state.restoreHex(upload['sha512state']).hexdigest()
        dir = os.path.join(hash[0:2], hash[2:4])
        absdir = os.path.join(self.assetstore['root'], dir)

        path = os.path.join(dir, hash)
        abspath = os.path.join(self.assetstore['root'], path)

        if not os.path.exists(absdir):
            os.makedirs(absdir)

        if os.path.exists(abspath):
            # Already have this file stored, just delete temp file.
            os.remove(upload['tempFile'])
        else:
            # Move the temp file to permanent location in the assetstore.
            shutil.move(upload['tempFile'], abspath)
            os.chmod(abspath, stat.S_IRUSR | stat.S_IWUSR)

        file['sha512'] = hash
        file['path'] = path

        return file

    def downloadFile(self, file, offset=0, headers=True):
        """
        Returns a generator function that will be used to stream the file from
        disk to the response.
        """
        path = os.path.join(self.assetstore['root'], file['path'])
        if not os.path.isfile(path):
            raise GirderException(
                'File %s does not exist.' % path,
                'girder.utility.filesystem_assetstore_adapter.'
                'file-does-not-exist')

        if headers:
            mimeType = file.get('mimeType', 'application/octet-stream')
            if not mimeType:
                mimeType = 'application/octet-stream'
            cherrypy.response.headers['Content-Type'] = mimeType
            cherrypy.response.headers['Content-Length'] = file['size'] - offset
            cherrypy.response.headers['Content-Disposition'] = \
                'attachment; filename="%s"' % file['name']

        def stream():
            with open(path, 'rb') as f:
                if offset > 0:
                    f.seek(offset)

                while True:
                    data = f.read(BUF_SIZE)
                    if not data:
                        break
                    yield data

        return stream

    def deleteFile(self, file):
        """
        Deletes the file from disk if it is the only File in this assetstore
        with the given sha512.
        """
        q = {
            'sha512': file['sha512'],
            'assetstoreId': self.assetstore['_id']
        }
        matching = ModelImporter().model('file').find(q, limit=2, fields=[])
        if matching.count(True) == 1:
            path = os.path.join(self.assetstore['root'], file['path'])
            if os.path.isfile(path):
                os.remove(path)

    def cancelUpload(self, upload):
        """
        Delete the temporary files associated with a given upload.
        """
        if os.path.exists(upload['tempFile']):
            os.unlink(upload['tempFile'])
