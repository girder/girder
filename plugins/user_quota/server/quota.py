#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2015 Kitware Inc.
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

import six

from bson.objectid import ObjectId, InvalidId
from girder import logger
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType
from girder.exceptions import GirderException, ValidationException, RestException
from girder.models.assetstore import Assetstore
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.item import Item
from girder.models.setting import Setting
from girder.models.upload import Upload
from girder.models.user import User
from girder.utility import assetstore_utilities
from girder.utility.system import formatSize
from . import constants


QUOTA_FIELD = 'quota'


def ValidateSizeQuota(value):
    """
    Validate a quota value.  This may be blank or a non-negative integer.

    :param value: The proposed value.
    :type value: int
    :returns: The validated value or None,
              and a recommended error message or None.
    :rtype: (int or None, str or None)
    """
    if value is None or value == '' or value == 0:
        return None, None
    error = False
    try:
        value = int(value)
        if value < 0:
            error = True
    except ValueError:
        error = True
    if error:
        return (value, 'Invalid quota.  Must be blank or a positive integer '
                       'representing the limit in bytes.')
    if value == 0:
        return None, None
    return value, None


class QuotaPolicy(Resource):
    def _filter(self, model, resource):
        """
        Filter a resource to include only the ordinary data and the quota
        field.

        :param model: the type of resource (e.g., user or collection)
        :param resource: the resource document.
        :returns: filtered field of the resource with the quota data, if any.
        """
        filtered = self.model(model).filter(resource, self.getCurrentUser())
        filtered[QUOTA_FIELD] = resource.get(QUOTA_FIELD, {})
        return filtered

    def _setResourceQuota(self, model, resource, policy):
        """
        Handle setting quota policies for any resource that supports them.

        :param model: the type of resource (e.g., user or collection)
        :param resource: the resource document.
        :param params: the query parameters.  'policy' is required and used.
        :returns: the updated resource document.
        """
        policy = self._validatePolicy(policy)
        if QUOTA_FIELD not in resource:
            resource[QUOTA_FIELD] = {}
        resource[QUOTA_FIELD].update(policy)
        self.model(model).save(resource, validate=False)
        return self._filter(model, resource)

    def _validate_fallbackAssetstore(self, value):
        """Validate the fallbackAssetstore parameter.

        :param value: the proposed value.
        :returns: the validated value: either None or 'current' to use the
                  current assetstore, 'none' to disable a fallback assetstore,
                  or an assetstore ID.
        """
        if not value or value == 'current':
            return None
        if value == 'none':
            return value
        try:
            value = ObjectId(value)
        except InvalidId:
            raise RestException(
                'Invalid fallbackAssetstore.  Must either be an assetstore '
                'ID, be blank or "current" to use the current assetstore, or '
                'be "none" to disable fallback usage.',
                extra='fallbackAssetstore')
        return value

    def _validate_fileSizeQuota(self, value):
        """Validate the fileSizeQuota parameter.

        :param value: the proposed value.
        :returns: the validated value
        :rtype: None or int
        """
        (value, err) = ValidateSizeQuota(value)
        if err:
            raise RestException(err, extra='fileSizeQuota')
        return value

    def _validate_preferredAssetstore(self, value):
        """Validate the preferredAssetstore parameter.

        :param value: the proposed value.
        :returns: the validated value: either None or 'current' to use the
                  current assetstore or an assetstore ID.
        """
        if not value or value == 'current':
            return None
        try:
            value = ObjectId(value)
        except InvalidId:
            raise RestException(
                'Invalid preferredAssetstore.  Must either be an assetstore '
                'ID, or be blank or "current" to use the current assetstore.',
                extra='preferredAssetstore')
        return value

    def _validate_useQuotaDefault(self, value):
        """Validate the useQuotaDefault parameter.

        :param value: the proposed value.
        :returns: the validated value
        :rtype: None or bool
        """
        if str(value).lower() in ('none', 'true', 'yes', '1'):
            return True
        if str(value).lower() in ('false', 'no', '0'):
            return False
        raise RestException(
            'Invalid useQuotaDefault.  Must either be true or false.',
            extra='useQuotaDefault')

    def _validatePolicy(self, policy):
        """
        Validate a policy JSON object.  Only a limited set of keys is
        supported, and each of them has a restricted data type.

        :param policy: JSON object to validate.  This may also be a Python
                           dictionary as if the JSON was already decoded.
        :returns: a validate policy dictionary.
        """
        validKeys = []
        for key in dir(self):
            if key.startswith('_validate_'):
                validKeys.append(key.split('_validate_', 1)[1])
        for key in list(policy):
            if key.startswith('_'):
                del policy[key]
        for key in policy:
            if key not in validKeys:
                raise RestException(
                    '%s is not a valid quota policy key.  Valid keys are %s.' %
                    (key, ', '.join(sorted(validKeys))))
            funcName = '_validate_' + key
            policy[key] = getattr(self, funcName)(policy[key])
        return policy

    @access.public
    @autoDescribeRoute(
        Description('Get quota and assetstore policies for the collection.')
        .modelParam('id', 'The collection ID', model=Collection, level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('Read permission denied on the collection.', 403)
    )
    def getCollectionQuota(self, collection):
        if QUOTA_FIELD not in collection:
            collection[QUOTA_FIELD] = {}
        collection[QUOTA_FIELD][
            '_currentFileSizeQuota'] = self._getFileSizeQuota('collection', collection)
        return self._filter('collection', collection)

    @access.public
    @autoDescribeRoute(
        Description('Set quota and assetstore policies for the collection.')
        .modelParam('id', 'The collection ID', model=Collection, level=AccessType.ADMIN)
        .jsonParam('policy', 'A JSON object containing the policies. This is a '
                   'dictionary of keys and values. Any key that is not specified '
                   'does not change.', requireObject=True)
        .errorResponse('ID was invalid.')
        .errorResponse('Read permission denied on the collection.', 403)
    )
    def setCollectionQuota(self, collection, policy):
        return self._setResourceQuota('collection', collection, policy)

    @access.public
    @autoDescribeRoute(
        Description('Get quota and assetstore policies for the user.')
        .modelParam('id', 'The user ID', model=User, level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('Read permission denied on the user.', 403)
    )
    def getUserQuota(self, user):
        if QUOTA_FIELD not in user:
            user[QUOTA_FIELD] = {}
        user[QUOTA_FIELD]['_currentFileSizeQuota'] = self._getFileSizeQuota('user', user)
        return self._filter('user', user)

    @access.public
    @autoDescribeRoute(
        Description('Set quota and assetstore policies for the user.')
        .modelParam('id', 'The user ID', model=User, level=AccessType.ADMIN)
        .jsonParam('policy', 'A JSON object containing the policies.  This is a '
                   'dictionary of keys and values.  Any key that is not specified '
                   'does not change.', requireObject=True)
        .errorResponse('ID was invalid.')
        .errorResponse('Read permission denied on the user.', 403)
    )
    def setUserQuota(self, user, policy):
        return self._setResourceQuota('user', user, policy)

    def _checkAssetstore(self, assetstoreSpec):
        """
        Check is a specified assetstore is available.

        :param assetstoreSpec: None for use current assetstore, 'none' to
                               disallow the assetstore, or an assetstore ID to
                               check if that assetstore exists and is nominally
                               available.
        :returns: None to use the current assetstore, False to indicate no
                  assetstore is allowed, or an assetstore document of an
                  allowed assetstore.
        """
        if assetstoreSpec is None:
            return None
        if assetstoreSpec == 'none':
            return False
        assetstore = Assetstore().load(id=assetstoreSpec)
        if not assetstore:
            return False
        adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
        if getattr(adapter, 'unavailable', False):
            return False
        return assetstore

    def _getBaseResource(self, model, resource):
        """
        Get the base resource for something pertaining to quota policies.  If
        the base resource has no quota policy, return (None, None).

        :param model: the initial model type.  Could be file, item, folder,
                      user, or collection.
        :param resource: the initial resource document.
        :returns: A pair ('model', 'resource'), where 'model' is the base model
                 type, either 'user' or 'collection'., and 'resource' is the
                 base resource document or the id of that document.
        """
        if isinstance(resource, tuple(list(six.string_types) + [ObjectId])):
            resource = self.model(model).load(id=resource, force=True)
        if model == 'file':
            model = 'item'
            resource = Item().load(id=resource['itemId'], force=True)
        if model in ('folder', 'item'):
            if ('baseParentType' not in resource or
                    'baseParentId' not in resource):
                resource = self.model(model).load(id=resource['_id'], force=True)
            if ('baseParentType' not in resource or
                    'baseParentId' not in resource):
                return None, None
            model = resource['baseParentType']
            resourceId = resource['baseParentId']
            resource = self.model(model).load(id=resourceId, force=True)
        if model in ('user', 'collection') and resource:
            # Ensure the base resource has a quota field so we can use the
            # default quota if appropriate
            if QUOTA_FIELD not in resource:
                resource[QUOTA_FIELD] = {}
        if not resource or QUOTA_FIELD not in resource:
            return None, None
        return model, resource

    def getUploadAssetstore(self, event):
        """
        Handle the model.upload.assetstore event.  This event passes a
        dictionary consisting of a model type and resource document.  If the
        base document has an assetstore policy, then set an assetstore key of
        this dictionary to an assetstore document that should be used or
        prevent the default action if no appropriate assetstores are allowed.

        :param event: event record.
        """
        model, resource = self._getBaseResource(event.info['model'],
                                                event.info['resource'])
        if resource is None:
            return
        policy = resource[QUOTA_FIELD]
        assetstore = self._checkAssetstore(
            policy.get('preferredAssetstore', None))
        if assetstore is False:
            assetstore = self._checkAssetstore(
                policy.get('fallbackAssetstore', None))
            if assetstore is not False:
                logger.info('preferredAssetstore not available for %s %s, '
                            'using fallbackAssetstore', model, resource['_id'])
        if assetstore is False:
            raise GirderException('Required assetstore is unavailable')
        if assetstore:
            event.addResponse(assetstore)

    def _getFileSizeQuota(self, model, resource):
        """
        Get the current fileSizeQuota for a resource.  This takes the default
        quota into account if necessary.

        :param model: the type of resource (e.g., user or collection)
        :param resource: the resource document.
        :returns: the fileSizeQuota.  None for no quota (unlimited), otherwise
                 a positive integer.
        """
        useDefault = resource[QUOTA_FIELD].get('useQuotaDefault', True)
        quota = resource[QUOTA_FIELD].get('fileSizeQuota', None)
        if useDefault:
            if model == 'user':
                key = constants.PluginSettings.QUOTA_DEFAULT_USER_QUOTA
            elif model == 'collection':
                key = constants.PluginSettings.QUOTA_DEFAULT_COLLECTION_QUOTA
            else:
                key = None
            if key:
                quota = Setting().get(key, None)
        if not quota or quota < 0 or not isinstance(quota, six.integer_types):
            return None
        return quota

    def _checkUploadSize(self, upload):
        """
        Check if an upload will fit within a quota restriction.

        :param upload: an upload document.
        :returns: None if the upload is allowed, otherwise a dictionary of
                  information about the quota restriction.
        """
        origSize = 0
        if 'fileId' in upload:
            file = File().load(id=upload['fileId'], force=True)
            origSize = int(file.get('size', 0))
            model, resource = self._getBaseResource('file', file)
        else:
            model, resource = self._getBaseResource(upload['parentType'], upload['parentId'])
        if resource is None:
            return None
        fileSizeQuota = self._getFileSizeQuota(model, resource)
        if not fileSizeQuota:
            return None
        newSize = resource['size'] + upload['size'] - origSize
        # always allow replacement with a smaller object
        if newSize <= fileSizeQuota or upload['size'] < origSize:
            return None
        left = fileSizeQuota - resource['size']
        if left < 0:
            left = 0
        return {'fileSizeQuota': fileSizeQuota,
                'sizeNeeded': upload['size'] - origSize,
                'quotaLeft': left,
                'quotaUsed': resource['size']}

    def checkUploadStart(self, event):
        """
        Check if an upload will fit within a quota restriction.  This is before
        the upload occurs, but since multiple uploads can be started
        concurrently, we also have to check when the upload is being completed.

        :param event: event record.
        """
        if '_id' in event.info:
            return
        quotaInfo = self._checkUploadSize(event.info)
        if quotaInfo:
            raise ValidationException(
                'Upload would exceed file storage quota (need %s, only %s '
                'available - used %s out of %s)' %
                (formatSize(quotaInfo['sizeNeeded']),
                 formatSize(quotaInfo['quotaLeft']),
                 formatSize(quotaInfo['quotaUsed']),
                 formatSize(quotaInfo['fileSizeQuota'])),
                field='size')

    def checkUploadFinalize(self, event):
        """
        Check if an upload will fit within a quota restriction before
        finalizing it.  If it doesn't, discard it.

        :param event: event record.
        """
        upload = event.info
        quotaInfo = self._checkUploadSize(upload)
        if quotaInfo:
            # Delete the upload
            Upload().cancelUpload(upload)
            raise ValidationException(
                'Upload exceeded file storage quota (need %s, only %s '
                'available - used %s out of %s)' %
                (formatSize(quotaInfo['sizeNeeded']),
                 formatSize(quotaInfo['quotaLeft']),
                 formatSize(quotaInfo['quotaUsed']),
                 formatSize(quotaInfo['fileSizeQuota'])),
                field='size')
