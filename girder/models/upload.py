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

import datetime
import six
from bson.objectid import ObjectId

from girder import events
from girder.constants import SettingKey
from girder.utility import assetstore_utilities
from .model_base import Model, ValidationException


class Upload(Model):
    """
    This model stores temporary records for uploads that have been approved
    but are not yet complete, so that they can be uploaded in chunks of
    arbitrary size. The chunks must be uploaded in order.
    """
    def initialize(self):
        self.name = 'upload'

    def uploadFromFile(self, obj, size, name, parentType=None, parent=None,
                       user=None, mimeType=None, reference=None):
        """
        This method wraps the entire upload process into a single function to
        facilitate "internal" uploads from a file-like object. Example:

        .. code-block:: python

            size = os.path.getsize(filename)

            with open(filename, 'rb') as f:
                self.model('upload').uploadFromFile(
                    f, size, filename, 'item', parentItem, user)

        :param obj: The object representing the content to upload.
        :type obj: file-like
        :param size: The total size of
        :param name: The name of the file to create.
        :type name: str
        :param parent: The parent (item or folder) to upload into.
        :type parent: dict
        :param parentType: The type of the parent: "folder" or "item".
        :type parentType: str
        :param user: The user who is creating the file.
        :type user: dict
        :param mimeType: MIME type of the file.
        :type mimeType: str
        :param reference: An optional reference string that will be sent to the
                          data.process event.
        :type reference: str
        """
        upload = self.createUpload(
            user=user, name=name, parentType=parentType, parent=parent,
            size=size, mimeType=mimeType, reference=reference)
        # The greater of 32 MB or the the upload minimum chunk size.
        chunkSize = max(self.model('setting').get(
            SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE), 32 * 1024**2)

        while True:
            data = obj.read(chunkSize)
            if not data:
                break

            upload = self.handleChunk(upload, six.BytesIO(data))

        return upload

    def validate(self, doc):
        if doc['size'] < 0:
            raise ValidationException('File size must not be negative.')
        if doc['received'] > doc['size']:
            raise ValidationException('Received too many bytes.')

        doc['updated'] = datetime.datetime.utcnow()

        return doc

    def handleChunk(self, upload, chunk):
        """
        When a chunk is uploaded, this should be called to process the chunk.
        If this is the final chunk of the upload, this method will finalize
        the upload automatically.

        :param upload: The upload document to update.
        :type upload: dict
        :param chunk: The file object representing the chunk that was uploaded.
        :type chunk: file
        """
        assetstore = self.model('assetstore').load(upload['assetstoreId'])
        adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)

        upload = self.save(adapter.uploadChunk(upload, chunk))

        # If upload is finished, we finalize it
        if upload['received'] == upload['size']:
            return self.finalizeUpload(upload, assetstore)
        else:
            return upload

    def requestOffset(self, upload):
        """
        Requests the offset that should be used to resume uploading. This
        makes the request from the assetstore adapter.
        """
        assetstore = self.model('assetstore').load(upload['assetstoreId'])
        adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
        return adapter.requestOffset(upload)

    def finalizeUpload(self, upload, assetstore=None):
        """
        This should only be called manually in the case of creating an
        empty file, i.e. one that has no chunks.

        :param upload: The upload document.
        :type upload: dict
        :param assetstore: If known, the containing assetstore for the upload.
        :type assetstore: dict
        :returns: The file object that was created.
        """
        events.trigger('model.upload.finalize', upload)
        if assetstore is None:
            assetstore = self.model('assetstore').load(upload['assetstoreId'])

        if 'fileId' in upload:  # Updating an existing file's contents
            file = self.model('file').load(upload['fileId'], force=True)

            # Delete the previous file contents from the containing assetstore
            assetstore_utilities.getAssetstoreAdapter(
                self.model('assetstore').load(
                    file['assetstoreId'])).deleteFile(file)

            item = self.model('item').load(file['itemId'], force=True)
            self.model('file').propagateSizeChange(
                item, upload['size'] - file['size'])

            # Update file info
            file['creatorId'] = upload['userId']
            file['created'] = datetime.datetime.utcnow()
            file['assetstoreId'] = assetstore['_id']
            file['size'] = upload['size']
        else:  # Creating a new file record
            if upload['parentType'] == 'folder':
                # Create a new item with the name of the file.
                item = self.model('item').createItem(
                    name=upload['name'], creator={'_id': upload['userId']},
                    folder={'_id': upload['parentId']})
            elif upload['parentType'] == 'item':
                item = self.model('item').load(
                    id=upload['parentId'], force=True)
            else:
                item = None

            file = self.model('file').createFile(
                item=item, name=upload['name'], size=upload['size'],
                creator={'_id': upload['userId']}, assetstore=assetstore,
                mimeType=upload['mimeType'], saveFile=False)

        adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
        file = self.model('file').save(adapter.finalizeUpload(upload, file))

        eventInfo = {'file': file, 'upload': upload}
        events.trigger('model.file.finalizeUpload.before', eventInfo)
        self.model('file').save(file)
        events.trigger('model.file.finalizeUpload.after', eventInfo)
        self.remove(upload)

        # Add an async event for handlers that wish to process this file.
        eventParams = {
            'file': file,
            'assetstore': assetstore
        }
        if 'reference' in upload:
            eventParams['reference'] = upload['reference']
        events.daemon.trigger('data.process', eventParams)

        return file

    def getTargetAssetstore(self, modelType, resource):
        """
        Get the assetstore for a particular target resource, i.e. where new
        data within the resource should be stored. In Girder core, this is
        always just the current assetstore, but plugins may override this
        behavior to allow for more granular assetstore selection.
        """
        eventParams = {'model': modelType, 'resource': resource}
        event = events.trigger('model.upload.assetstore', eventParams)

        if event.responses:
            assetstore = event.responses[-1]
        elif 'assetstore' in eventParams:
            # This mode of event response is deprecated, but is preserved here
            # for backward compatibility
            # TODO remove in v2.0
            assetstore = eventParams['assetstore']
        else:
            assetstore = self.model('assetstore').getCurrent()

        return assetstore

    def createUploadToFile(self, file, user, size, reference=None):
        """
        Creates a new upload record into a file that already exists. This
        should be used when updating the contents of a file. Deletes any
        previous file content from the assetstore it was in. This will upload
        into the current assetstore rather than assetstore the file was
        previously contained in.

        :param file: The file record to update.
        :param user: The user performing this upload.
        :param size: The size of the new file contents.
        :param reference: An optional reference string that will be sent to the
                          data.process event.
        :type reference: str
        """
        assetstore = self.getTargetAssetstore('file', file)
        adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
        now = datetime.datetime.utcnow()

        upload = {
            'created': now,
            'updated': now,
            'userId': user['_id'],
            'fileId': file['_id'],
            'assetstoreId': assetstore['_id'],
            'size': size,
            'name': file['name'],
            'mimeType': file['mimeType'],
            'received': 0
        }
        if reference is not None:
            upload['reference'] = reference
        upload = adapter.initUpload(upload)
        return self.save(upload)

    def createUpload(self, user, name, parentType, parent, size, mimeType=None,
                     reference=None):
        """
        Creates a new upload record, and creates its temporary file
        that the chunks will be written into. Chunks should then be sent
        in order using the _id of the upload document generated by this method.

        :param user: The user performing the upload.
        :type user: dict
        :param name: The name of the file being uploaded.
        :type name: str
        :param parentType: The type of the parent being uploaded into.
        :type parentType: str ('folder' or 'item')
        :param parent: The document representing the parent.
        :type parentId: dict
        :param size: Total size in bytes of the whole file.
        :type size: int
        :param mimeType: The mimeType of the file.
        :type mimeType: str
        :param reference: An optional reference string that will be sent to the
                          data.process event.
        :type reference: str
        :returns: The upload document that was created.
        """
        assetstore = self.getTargetAssetstore(parentType, parent)
        adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
        now = datetime.datetime.utcnow()

        if not mimeType:
            mimeType = 'application/octet-stream'
        upload = {
            'created': now,
            'updated': now,
            'assetstoreId': assetstore['_id'],
            'size': size,
            'name': name,
            'mimeType': mimeType,
            'received': 0
        }
        if reference is not None:
            upload['reference'] = reference

        if parentType and parent:
            upload['parentType'] = parentType.lower()
            upload['parentId'] = ObjectId(parent['_id'])
        else:
            upload['parentType'] = None
            upload['parentId'] = None

        if user:
            upload['userId'] = user['_id']
        else:
            upload['userId'] = None

        upload = adapter.initUpload(upload)
        return self.save(upload)

    def list(self, limit=0, offset=0, sort=None, filters=None):
        """
        Search for uploads or simply list all visible uploads.

        :param limit: Result set size limit.
        :param offset: Offset into the results.
        :param sort: The sort direction.
        :param filters: if not None, a dictionary that can contain ids that
                        must match the uploads, plus an minimumAge value.
        """
        query = {}
        if filters:
            for key in ('uploadId', 'userId', 'parentId', 'assetstoreId'):
                if key in filters:
                    id = filters[key]
                    if id and not isinstance(id, ObjectId):
                        id = ObjectId(id)
                    if id:
                        if key == 'uploadId':
                            query['_id'] = id
                        else:
                            query[key] = id
            if 'minimumAge' in filters:
                query['updated'] = {
                    '$lte': datetime.datetime.utcnow() -
                    datetime.timedelta(days=float(filters['minimumAge']))
                    }
        # Perform the find; we'll do access-based filtering of the result
        # set afterward.
        return self.find(query, limit=limit, sort=sort, offset=offset)

    def cancelUpload(self, upload):
        """
        Discard an upload that is in progress.  This asks the assetstore to
        discard the data, then removes the item from the upload database.

        :param upload: The upload document to remove.
        :type upload: dict
        """
        assetstore = self.model('assetstore').load(upload['assetstoreId'])
        # If the assetstore was deleted, the upload may still be in our
        # database
        if assetstore:
            adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
            try:
                adapter.cancelUpload(upload)
            except ValidationException:
                # this assetstore is currently unreachable, so skip it
                pass
        self.model('upload').remove(upload)

    def untrackedUploads(self, action='list', assetstoreId=None):
        """
        List or discard any uploads that an assetstore knows about but that our
        database doesn't have in it.

        :param action: 'delete' to discard the untracked uploads, anything else
            to just return with a list of them.
        :type action: str
        :param assetstoreId: if present, only include untracked items from the
            specified assetstore.
        :type assetstoreId: str
        :returns: a list of items that were removed or could be removed.
        """
        results = []
        knownUploads = list(self.list())
        # Iterate through all assetstores
        for assetstore in self.model('assetstore').list():
            if assetstoreId and assetstoreId != assetstore['_id']:
                continue
            adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
            try:
                results.extend(adapter.untrackedUploads(
                    knownUploads, delete=(action == 'delete')))
            except ValidationException:
                # this assetstore is currently unreachable, so skip it
                pass
        return results
