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
import time
import uuid

from girder import logger
from girder.api.rest import setResponseHeader
from girder.external.mongodb_proxy import MongoProxy
from girder.models import getDbConnection
from girder.exceptions import ValidationException
from girder.models.file import File
from . import hash_state
from .abstract_assetstore_adapter import AbstractAssetstoreAdapter


# 2MB chunks. Clients must not send any chunks that are smaller than this
# unless they are sending the final chunk.
CHUNK_SIZE = 2097152

# Cache recent connections so we can skip some start up actions
RECENT_CONNECTION_CACHE_TIME = 600  # seconds
RECENT_CONNECTION_CACHE_MAX_SIZE = 100
_recentConnections = {}


def _ensureChunkIndices(collection):
    """
    Ensure that we have appropriate indices on the chunk collection.

    :param collection: a connection to a mongo collection.
    """
    collection.create_index([
        ('uuid', pymongo.ASCENDING),
        ('n', pymongo.ASCENDING)
    ], unique=True)


def _setupSharding(collection, keyname='uuid'):
    """
    If we are communicating with a sharded server, and the collection is not
    sharded, ask for it to be sharded based on a key.

    :param collection: a connection to a mongo collection.
    :param keyname: the name of the key to shard on.
    :returns: True if sharding was added, False if it could not be added, or
        'present' if already sharded.
    """
    database = collection.database
    client = database.client
    stat = client.admin.command('serverStatus')
    # sharding will be non-None if the client is communicating with a mongos
    # instance. For mongo 3.0 we have to check the process name for 'mongos'.
    if not stat.get('sharding') and 'mongos' not in stat.get('process', ''):
        return False
    if database.command('collstats', collection.name).get('sharded'):
        return 'present'
    try:
        client.admin.command('enableSharding', database.name)
    except pymongo.errors.OperationFailure:
        # sharding may already be enabled
        pass
    try:
        client.admin.command(
            'shardCollection', '%s.%s' % (database.name, collection.name),
            key={keyname: 1})
        return True
    except pymongo.errors.OperationFailure:
        pass
    return False


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
                doc.get('mongohost'), doc.get('replicaset'), autoRetry=False,
                serverSelectionTimeoutMS=10000)[doc['db']].chunk
            _ensureChunkIndices(chunkColl)
        except pymongo.errors.ServerSelectionTimeoutError as e:
            raise ValidationException(
                'Could not connect to the database: %s' % str(e))

        return doc

    @staticmethod
    def fileIndexFields():
        return ['sha512', 'chunkUuid']

    def __init__(self, assetstore):
        """
        :param assetstore: The assetstore to act on.
        """
        super(GridFsAssetstoreAdapter, self).__init__(assetstore)
        recent = False
        try:
            # Guard in case the connectionArgs is unhashable
            key = (self.assetstore.get('mongohost'),
                   self.assetstore.get('replicaset'),
                   self.assetstore.get('shard'))
            if key in _recentConnections:
                recent = (time.time() - _recentConnections[key]['created'] <
                          RECENT_CONNECTION_CACHE_TIME)
        except TypeError:
            key = None
        try:
            # MongoClient automatically reuses connections from a pool, but we
            # want to avoid redoing ensureChunkIndices each time we get such a
            # connection.
            client = getDbConnection(self.assetstore.get('mongohost'),
                                     self.assetstore.get('replicaset'),
                                     quiet=recent)
            self.chunkColl = MongoProxy(client[self.assetstore['db']].chunk)
            if not recent:
                _ensureChunkIndices(self.chunkColl)
                if self.assetstore.get('shard') == 'auto':
                    _setupSharding(self.chunkColl)
                if key is not None:
                    if len(_recentConnections) >= RECENT_CONNECTION_CACHE_MAX_SIZE:
                        _recentConnections.clear()
                    _recentConnections[key] = {
                        'created': time.time()
                    }
        except pymongo.errors.ConnectionFailure:
            logger.error('Failed to connect to GridFS assetstore %s',
                         self.assetstore['db'])
            self.chunkColl = 'Failed to connect'
            self.unavailable = True
        except pymongo.errors.ConfigurationError:
            logger.exception('Failed to configure GridFS assetstore %s',
                             self.assetstore['db'])
            self.chunkColl = 'Failed to configure'
            self.unavailable = True

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

        # TODO: when saving uploads is optional, we can conditionally try to
        # fetch the last chunk.  Add these line before `lastChunk = ...`:
        #   lastChunk = None
        #   if '_id' in upload or upload['received'] != 0:
        lastChunk = self.chunkColl.find_one({
            'uuid': upload['chunkUuid']
        }, projection=['n'], sort=[('n', pymongo.DESCENDING)])
        if lastChunk:
            # This bit of code will only do anything if there is a discrepancy
            # between the received count of the upload record and the length of
            # the file stored as chunks in the database. This code updates the
            # sha512 state with the difference before reading the bytes sent
            # from the user.
            if self.requestOffset(upload) > upload['received']:
                # This isn't right -- the last received amount may not be a
                # complete chunk.
                cursor = self.chunkColl.find({
                    'uuid': upload['chunkUuid'],
                    'n': {'$gte': upload['received'] // CHUNK_SIZE}
                }, projection=['data']).sort('n', pymongo.ASCENDING)
                for result in cursor:
                    checksum.update(result['data'])
        n = lastChunk['n'] + 1 if lastChunk else 0

        size = 0
        startingN = n

        while upload['received']+size < upload['size']:
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
            })
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
        lastChunk = self.chunkColl.find_one({
            'uuid': upload['chunkUuid']
        }, projection=['n'], sort=[('n', pymongo.DESCENDING)])

        if lastChunk is None:
            offset = 0
        else:
            offset = lastChunk['n'] * CHUNK_SIZE
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

                if position + chunkLen - co > endByte:
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
        matching = File().find(q, limit=2, projection=[])
        if matching.count(True) == 1:
            # If we can't reach the database, we return anyway.  A system check
            # will be necessary to remove the abandoned file.  Since we already
            # can handle that case, tell Mongo to use a 0 write concern -- we
            # don't need to know that the chunks have been deleted, and this
            # can be faster.
            try:
                self.chunkColl.with_options(
                    write_concern=pymongo.WriteConcern(w=0)).delete_many(
                        {'uuid': file['chunkUuid']})
            except pymongo.errors.AutoReconnect:
                pass

    def cancelUpload(self, upload):
        """
        Delete all of the chunks associated with a given upload.
        """
        self.chunkColl.delete_many({'uuid': upload['chunkUuid']})
