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
import cherrypy
import pymongo
import uuid

from StringIO import StringIO
from .model_importer import ModelImporter
from girder import logger
from girder.models import getDbConnection
from girder.models.model_base import ValidationException

from hashlib import sha512
from . import sha512_state
from .abstract_assetstore_adapter import AbstractAssetstoreAdapter


# 2MB chunks. Clients must not send any chunks that are smaller than this
# unless they are sending the final chunk.
CHUNK_SIZE = 2097152


class GridFsAssetstoreAdapter(AbstractAssetstoreAdapter):
    """
    This assetstore type stores files within mongoDB using the GridFS data
    model.
    """

    @staticmethod
    def validateInfo(doc):
        """
        Makes sure the database name is valid.
        """
        if not doc.get('db', ''):
            raise ValidationException('Database name must not be empty.', 'db')
        if '.' in doc['db'] or ' ' in doc['db']:
            raise ValidationException('Database name cannot contain spaces'
                                      ' or periods.', 'db')
        return doc

    @staticmethod
    def fileIndexFields():
        return ['sha512']

    def __init__(self, assetstore):
        """
        :param assetstore: The assetstore to act on.
        """
        self.assetstore = assetstore
        try:
            self.chunkColl = getDbConnection(
                assetstore.get('mongohost', None),
                assetstore.get('replicaset', None))[assetstore['db']]['chunk']
        except pymongo.errors.ConnectionFailure:
            logger.error('Failed to connect to GridFS assetstore %s',
                         assetstore['db'])
            self.chunkColl = 'Failed to connect'
            self.unavailable = True
            return
        except pymongo.errors.ConfigurationError:
            logger.exception('Failed to configure GridFS assetstore %s',
                             assetstore['db'])
            self.chunkColl = 'Failed to configure'
            self.unavailable = True
            return
        self.chunkColl.ensure_index([
            ('uuid', pymongo.ASCENDING),
            ('n', pymongo.ASCENDING)
        ], unique=True)

    def initUpload(self, upload):
        """
        Creates a UUID that will be used to uniquely link each chunk to
        """
        upload['chunkUuid'] = uuid.uuid4().hex
        upload['sha512state'] = sha512_state.serializeHex(sha512())
        return upload

    def uploadChunk(self, upload, chunk):
        """
        Stores the uploaded chunk in fixed-sized pieces in the chunks
        collection of this assetstore's database.
        """
        # If we know the chunk size is too large or small, fail early.
        self.checkUploadSize(upload, self.getChunkSize(chunk))

        if isinstance(chunk, basestring):
            if isinstance(chunk, unicode):
                chunk = chunk.encode('utf8')
            chunk = StringIO(chunk)

        # Restore the internal state of the streaming SHA-512 checksum
        checksum = sha512_state.restoreHex(upload['sha512state'])

        # This bit of code will only do anything if there is a discrepancy
        # between the received count of the upload record and the length of
        # the file stored as chunks in the database. This code simply updates
        # the sha512 state with the difference before reading the bytes sent
        # from the user.
        if self.requestOffset(upload) > upload['received']:
            cursor = self.chunkColl.find({
                'uuid': upload['chunkUuid'],
                'n': {'$gte': upload['received'] // CHUNK_SIZE}
            }, fields=['data']).sort('n', pymongo.ASCENDING)
            for result in cursor:
                checksum.update(result['data'])

        cursor = self.chunkColl.find({
            'uuid': upload['chunkUuid']
        }, fields=['n']).sort('n', pymongo.DESCENDING).limit(1)
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
                self.chunkColl.insert({
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
            self.chunkColl.remove({'uuid': upload['chunkUuid'],
                                   'n': {'$gte': startingN}}, multi=True)
            raise

        # Persist the internal state of the checksum
        upload['sha512state'] = sha512_state.serializeHex(checksum)
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
        }, fields=['n']).sort('n', pymongo.DESCENDING).limit(1)
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
        hash = sha512_state.restoreHex(upload['sha512state']).hexdigest()

        file['sha512'] = hash
        file['chunkUuid'] = upload['chunkUuid']
        file['chunkSize'] = CHUNK_SIZE

        return file

    def downloadFile(self, file, offset=0, headers=True):
        """
        Returns a generator function that will be used to stream the file from
        the database to the response.
        """
        if headers:
            mimeType = file.get('mimeType', 'application/octet-stream')
            if not mimeType:
                mimeType = 'application/octet-stream'
            cherrypy.response.headers['Content-Type'] = mimeType
            cherrypy.response.headers['Content-Length'] = file['size'] - offset
            cherrypy.response.headers['Content-Disposition'] = \
                'attachment; filename="%s"' % file['name']

        # If the file is empty, we stop here
        if file['size'] - offset <= 0:
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
        }, fields=['data']).sort('n', pymongo.ASCENDING)

        def stream():
            co = chunkOffset  # Can't assign to outer scope without "nonlocal"
            for chunk in cursor:
                if co > 0:
                    yield chunk['data'][co:]
                    co = 0
                else:
                    yield chunk['data']

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
        matching = ModelImporter().model('file').find(q, limit=2, fields=[])
        if matching.count(True) == 1:
            try:
                self.chunkColl.remove({'uuid': file['chunkUuid']})
            except pymongo.errors.AutoReconnect:
                # we can't reach the database.  Go ahead and return; a system
                # check will be necessary to remove the abandoned file
                pass

    def cancelUpload(self, upload):
        """
        Delete all of the chunks associated with a given upload.
        """
        self.chunkColl.remove({'uuid': upload['chunkUuid']})
