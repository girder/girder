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

from .model_base import Model
from girder.constants import AssetstoreType, SortDir
from girder.exceptions import ValidationException, GirderException, NoAssetstoreAdapter
from girder.utility import assetstore_utilities
from girder.utility.abstract_assetstore_adapter import AbstractAssetstoreAdapter


class Assetstore(Model):
    """
    This model represents an assetstore, an abstract repository of Files.
    """
    def initialize(self):
        self.name = 'assetstore'

    def validate(self, doc):
        # Ensure no duplicate names
        q = {'name': doc['name']}
        if '_id' in doc:
            q['_id'] = {'$ne': doc['_id']}
        duplicate = self.findOne(q, fields=['_id'])
        if duplicate is not None:
            raise ValidationException('An assetstore with that name already '
                                      'exists.', 'name')

        # Name must not be empty
        if not doc['name']:
            raise ValidationException('Name must not be empty.', 'name')

        # Adapter classes validate each type internally
        adapter = assetstore_utilities.getAssetstoreAdapter(doc, instance=False)
        adapter.validateInfo(doc)

        # If no current assetstore exists yet, set this one as the current.
        current = self.findOne({'current': True}, fields=['_id'])
        if current is None:
            doc['current'] = True
        if 'current' not in doc:
            doc['current'] = False

        # If we are setting this as current, we should unmark all other
        # assetstores that have the current flag.
        if doc['current'] is True:
            self.update({'current': True}, {'$set': {'current': False}})

        return doc

    def remove(self, assetstore, **kwargs):
        """
        Delete an assetstore. If there are any files within this assetstore,
        a validation exception is raised.

        :param assetstore: The assetstore document to delete.
        :type assetstore: dict
        """
        from .file import File

        files = File().findOne({'assetstoreId': assetstore['_id']})
        if files is not None:
            raise ValidationException('You may not delete an assetstore that contains files.')
        # delete partial uploads before we delete the store.
        adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
        try:
            adapter.untrackedUploads([], delete=True)
        except ValidationException:
            # this assetstore is currently unreachable, so skip this step
            pass
        # now remove the assetstore
        Model.remove(self, assetstore)
        # If after removal there is no current assetstore, then pick a
        # different assetstore to be the current one.
        current = self.findOne({'current': True})
        if current is None:
            first = self.findOne(sort=[('created', SortDir.DESCENDING)])
            if first is not None:
                first['current'] = True
                self.save(first)

    def list(self, limit=0, offset=0, sort=None):
        """
        List all assetstores.

        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        :returns: List of users.
        """
        cursor = self.find({}, limit=limit, offset=offset, sort=sort)
        for assetstore in cursor:
            self.addComputedInfo(assetstore)
            yield assetstore

    def addComputedInfo(self, assetstore):
        """
        Add all runtime-computed properties about an assetstore to its document.

        :param assetstore: The assetstore object.
        :type assetstore: dict
        """
        from .file import File

        try:
            adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
        except NoAssetstoreAdapter:
            # If the adapter doesn't exist, use the abstract adapter, since
            # this will just give the default capacity information
            adapter = AbstractAssetstoreAdapter(assetstore)
        assetstore['capacity'] = adapter.capacityInfo()
        assetstore['hasFiles'] = File().findOne({'assetstoreId': assetstore['_id']}) is not None

    def createFilesystemAssetstore(self, name, root, perms=None):
        return self.save({
            'type': AssetstoreType.FILESYSTEM,
            'created': datetime.datetime.utcnow(),
            'name': name,
            'root': root,
            'perms': perms
        })

    def createGridFsAssetstore(self, name, db, mongohost=None,
                               replicaset=None, shard=None):
        return self.save({
            'type': AssetstoreType.GRIDFS,
            'created': datetime.datetime.utcnow(),
            'name': name,
            'db': db,
            'mongohost': mongohost,
            'replicaset': replicaset,
            'shard': shard
        })

    def createS3Assetstore(self, name, bucket, accessKeyId, secret, prefix='',
                           service='', readOnly=False, region=None, inferCredentials=False,
                           serverSideEncryption=False):
        return self.save({
            'type': AssetstoreType.S3,
            'created': datetime.datetime.utcnow(),
            'name': name,
            'accessKeyId': accessKeyId,
            'secret': secret,
            'readOnly': readOnly,
            'prefix': prefix,
            'bucket': bucket,
            'service': service,
            'region': region,
            'inferCredentials': inferCredentials,
            'serverSideEncryption': serverSideEncryption
        })

    def getCurrent(self):
        """
        Returns the current assetstore. If none exists, this will raise a 500
        exception.
        """
        current = self.findOne({'current': True})
        if current is None:
            raise GirderException(
                'No current assetstore is set.',
                'girder.model.assetstore.no-current-assetstore')

        return current

    def importData(self, assetstore, parent, parentType, params, progress,
                   user, **kwargs):
        """
        Calls the importData method of the underlying assetstore adapter.
        """
        adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
        return adapter.importData(
            parent=parent, parentType=parentType, params=params,
            progress=progress, user=user, **kwargs)
