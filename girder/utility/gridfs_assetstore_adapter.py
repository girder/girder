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

import bson
from hashlib import sha512
import pymongo
import six
from six import BytesIO
import uuid

from girder import logger
from girder.api.rest import setResponseHeader
from girder.models import getDbConnection
from girder.models.model_base import ValidationException
from . import hash_state
from .abstract_assetstore_adapter import AbstractAssetstoreAdapter


# 2MB chunks. Clients must not send any chunks that are smaller than this
# unless they are sending the final chunk.
CHUNK_SIZE = 2097152


def _ensureChunkIndices(collection):
    """
    Ensure that we have appropriate indices on the chunk collection.
    """
    collection.create_index([
        ('uuid', pymongo.ASCENDING),
        ('n', pymongo.ASCENDING)
    ], unique=True)


class GridFsAssetstoreAdapter(AbstractAssetstoreAdapter):
    """
    This assetstore type stores files within MongoDB using the GridFS data
    model.
    """

    @staticmethod
    def validateInfo(doc):
        """
        Validate the assetstore -- make sure we can connect to it and that the
        necessary indexes are set up.
        """
        if not doc.get('db', ''):
            raise ValidationException('Database name must not be empty.', 'db')
        if '.' in doc['db'] or ' ' in doc['db']:
            raise ValidationException('Database name cannot contain spaces'
                                      ' or periods.', 'db')

        try:
            chunkColl = getDbConnection(
                doc.get('mongohost', None), doc.get('replicaset', None),
                autoRetry=False,
                serverSelectionTimeoutMS=10000)[doc['db']].chunk
            _ensureChunkIndices(chunkColl)
        except pymongo.errors.ServerSelectionTimeoutError as e:
            raise ValidationException(
                'Could not connect to the database: %s' % str(e))

        return doc

    @staticmethod
    def fileIndexFields():
        return ['sha512']

    def __init__(self, assetstore):
        """
        :param assetstore: The assetstore to act on.
        """
        super(GridFsAssetstoreAdapter, self).__init__(assetstore)
        try:
            self.chunkColl = getDbConnection(
                self.assetstore.get('mongohost', None),
                self.assetstore.get('replicaset', None)
            )[self.assetstore['db']].chunk
            _ensureChunkIndices(self.chunkColl)
        except pymongo.errors.ConnectionFailure:
            logger.error('Failed to connect to GridFS assetstore %s',
                         self.assetstore['db'])
            self.chunkColl = 'Failed to connect'
            self.unavailable = True
            return
        except pymongo.errors.ConfigurationError:
            logger.exception('Failed to configure GridFS assetstore %s',
                             self.assetstore['db'])
            self.chunkColl = 'Failed to configure'
            self.unavailable = True
            return

    def initUpload(self, upload):
        """
        Creates a UUID that will be used to uniquely link each chunk to
        """
        upload['chunkUuid'] = uuid.uuid4().hex
        upload['sha512state'] = hash_state.serializeHex(sha512())
        return upload

    def uploadChunk(self, upload, chunk):
        """
        Stores the uploaded chunk in fixed-sized pieces in the chunks
        collection of this assetstore's database.
        """
        # If we know the chunk size is too large or small, fail early.
        self.checkUploadSize(upload, self.getChunkSize(chunk))

        if isinstance(chunk, six.text_type):
            chunk = chunk.encode('utf8')

        if isinstance(chunk, six.binary_type):
            chunk = BytesIO(chunk)

        # Restore the internal state of the streaming SHA-512 checksum
        checksum = hash_state.restoreHex(upload['sha512state'], 'sha512')

        # This bit of code will only do anything if there is a discrepancy
        # between the received count of the upload record and the length of
        # the file stored as chunks in the database. This code simply updates
        # the sha512 state with the difference before reading the bytes sent
        # from the user.
        if self.requestOffset(upload) > upload['received']:
            cursor = self.chunkColl.find({
                'uuid': upload['chunkUuid'],
                'n': {'$gte': upload['received'] // CHUNK_SIZE}
            }, projection=['data']).sort('n', pymongo.ASCENDING)
            for result in cursor:
                checksum.update(result['data'])

        cursor = self.chunkColl.find({
            'uuid': upload['chunkUuid']
        }, projection=['n']).sort('n', pymongo.DESCENDING).limit(1)
        if cursor.count(True) == 0:
            n = 0
        else:
            n = cursor[0]['n'] + 1

        size = 0
        startingN = n

        while not upload['received']+size > upload['size']:
            data = chunk.read(CHUNK_SIZE)
            if not data:
                break
            # If a timeout occurs while we are trying to load data, we might
            # have succeeded, in which case we will get a DuplicateKeyError
            # when it automatically retries.  Therefore, log this error but
            # don't stop.
            try:
                self.chunkColl.insert_one({
                    'n': n,
                    'uuid': upload['chunkUuid'],
                    'data': bson.binary.Binary(data)
                })
            except pymongo.errors.DuplicateKeyError:
                logger.info('Received a DuplicateKeyError while uploading, '
                            'probably because we reconnected to the database '
                            '(chunk uuid %s part %d)', upload['chunkUuid'], n)
            n += 1
            size += len(data)
            checksum.update(data)
        chunk.close()

        try:
            self.checkUploadSize(upload, size)
        except ValidationException:
            # The user tried to upload too much or too little.  Delete
            # everything we added
            self.chunkColl.delete_many({
                'uuid': upload['chunkUuid'],
                'n': {'$gte': startingN}
            }, multi=True)
            raise

        # Persist the internal state of the checksum
        upload['sha512state'] = hash_state.serializeHex(checksum)
        upload['received'] += size
        return upload

    def requestOffset(self, upload):
        """
        The offset will be the CHUNK_SIZE * total number of chunks in the
        database for this file. We return the max of that and the received
        count because in testing mode we are uploading chunks that are smaller
        than the CHUNK_SIZE, which in practice will not work.
        """
        cursor = self.chunkColl.find({
            'uuid': upload['chunkUuid']
        }, projection=['n']).sort('n', pymongo.DESCENDING).limit(1)
        if cursor.count(True) == 0:
            offset = 0
        else:
            offset = cursor[0]['n'] * CHUNK_SIZE

        return max(offset, upload['received'])

    def finalizeUpload(self, upload, file):
        """
        Grab the final state of the checksum and set it on the file object,
        and write the generated UUID into the file itself.
        """
        hash = hash_state.restoreHex(upload['sha512state'],
                                     'sha512').hexdigest()

        file['sha512'] = hash
        file['chunkUuid'] = upload['chunkUuid']
        file['chunkSize'] = CHUNK_SIZE

        return file

    def downloadFile(self, file, offset=0, headers=True, endByte=None,
                     contentDisposition=None, extraParameters=None, **kwargs):
        """
        Returns a generator function that will be used to stream the file from
        the database to the response.
        """
        if endByte is None or endByte > file['size']:
            endByte = file['size']

        if headers:
            setResponseHeader('Accept-Ranges', 'bytes')
            self.setContentHeaders(file, offset, endByte, contentDisposition)

        # If the file is empty, we stop here
        if endByte - offset <= 0:
            return lambda: ''

        n = 0
        chunkOffset = 0

        # We must "seek" to the correct chunk index and local offset
        if offset > 0:
            n = offset // file['chunkSize']
            chunkOffset = offset % file['chunkSize']

        cursor = self.chunkColl.find({
            'uuid': file['chunkUuid'],
            'n': {'$gte': n}
        }, projection=['data']).sort('n', pymongo.ASCENDING)

        def stream():
            co = chunkOffset  # Can't assign to outer scope without "nonlocal"
            position = offset
            shouldBreak = False

            for chunk in cursor:
                chunkLen = len(chunk['data'])

                if position + chunkLen > endByte:
                    chunkLen = endByte - position + co
                    shouldBreak = True

                yield chunk['data'][co:chunkLen]

                if shouldBreak:
                    break

                position += chunkLen - co

                if co > 0:
                    co = 0

        return stream

    def deleteFile(self, file):
        """
        Delete all of the chunks in the collection that correspond to the
        given file.
        """
        q = {
            'chunkUuid': file['chunkUuid'],
            'assetstoreId': self.assetstore['_id']
        }
        matching = self.model('file').find(q, limit=2, projection=[])
        if matching.count(True) == 1:
            try:
                self.chunkColl.delete_many({'uuid': file['chunkUuid']})
            except pymongo.errors.AutoReconnect:
                # we can't reach the database.  Go ahead and return; a system
                # check will be necessary to remove the abandoned file
                pass

    def cancelUpload(self, upload):
        """
        Delete all of the chunks associated with a given upload.
        """
        self.chunkColl.delete_many({'uuid': upload['chunkUuid']})
