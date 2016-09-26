#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
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

import copy
import datetime
import six

from bson.objectid import ObjectId
from girder import events
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, RestException
from girder.constants import AccessType
from girder.models.model_base import AccessControlledModel
from girder.utility import acl_mixin
from . import constants


class ResourceExt(Resource):
    def __init__(self, info):
        """
        Initialize the resource.  This saves the info path so that we can
        dynamically change the routes when the setting listing the resources we
        use changes.
        :param info: the info class passed to the load function.
        """
        super(ResourceExt, self).__init__()
        self.loadInfo = info
        self.boundResources = {}

    # These methods implement the endpoint routing

    def bindModels(self, event=None):
        """
        When the list of tracked provenance resources is changed, rebind the
        appropriate models to this instance of this class.
        :param event: the event when a setting is saved, or None to check the
                      binding.
        """
        if not event or event.name == 'provenance.initialize':
            pass
        elif event.name == 'model.setting.save.after':
            if not hasattr(event, "info"):
                return
            if (event.info.get('key', '') !=
                    constants.PluginSettings.PROVENANCE_RESOURCES):
                return
        else:
            return
        resources = self.model('setting').get(
            constants.PluginSettings.PROVENANCE_RESOURCES)
        if resources:
            resources = resources.replace(',', ' ').strip().split()
        else:
            resources = []
        resources = dict.fromkeys(resources)
        # Always include item
        resources['item'] = None
        # Exclude resources that should never have provenance
        for disallowedResource in ('model_base', 'notification', 'password',
                                   'token'):
            if disallowedResource in resources:
                del resources[disallowedResource]
        self.unbindModels(resources)
        for resource in resources:
            if resource not in self.boundResources:
                events.bind('model.%s.save' % resource, 'provenance',
                            self.resourceSaveHandler)
                events.bind('model.%s.copy.prepare' % resource,
                            'provenance', self.resourceCopyHandler)
                if hasattr(self.loadInfo['apiRoot'], resource):
                    getattr(self.loadInfo['apiRoot'], resource).route(
                        'GET', (':id', 'provenance'),
                        self.getGetHandler(resource))
                self.boundResources[resource] = True

    def unbindModels(self, resources={}):
        """
        Unbind any models that were bound and aren't listed as needed.
        :param resources: resources that shouldn't be unbound.
        """
        # iterate over a list so that we can change the dictionary as we use it
        for oldresource in list(six.viewkeys(self.boundResources)):
            if oldresource not in resources:
                # Unbind this and remove it from the api
                events.unbind('model.%s.save' % oldresource, 'provenance')
                events.unbind('model.%s.copy.prepare' % oldresource,
                              'provenance')
                if hasattr(self.loadInfo['apiRoot'], oldresource):
                    getattr(self.loadInfo['apiRoot'], oldresource).removeRoute(
                        'GET', (':id', 'provenance'),
                        self.getGetHandler(oldresource))
                del self.boundResources[oldresource]

    def getGetHandler(self, resource):
        """
        Return a function that will get the provenance for a particular
        resource type.  This creates such a function if necessary, copying the
        main function and setting an internal value so that the function is
        coupled to the resource.
        :param resource: the name of the resource to get.
        :returns: getHandler function.
        """
        key = 'provenanceGetHandler_%s' % resource
        if not hasattr(self, key):
            def resourceGetHandler(id, params):
                return self.provenanceGetHandler(id, params, resource)
            # We inherit the description and access decorator details from the
            # general provenanceGetHandler
            for attr in ('description', 'accessLevel'):
                setattr(resourceGetHandler, attr,
                        getattr(self.provenanceGetHandler, attr))
            setattr(self, key, resourceGetHandler)
        return getattr(self, key)

    @access.public
    @describeRoute(
        Description('Get the provenance for a given resource.')
        .param('id', 'The resource ID', paramType='path')
        .param('version', 'The provenance version for the resource.  If not '
               'specified, the latest provenance data is returned.  If "all" '
               'is specified, a list of all provenance data is returned.  '
               'Negative indices can also be used (-1 is the latest '
               'provenance, -2 second latest, etc.).', required=False)
        .errorResponse()
    )
    def provenanceGetHandler(self, id, params, resource=None):
        user = self.getCurrentUser()
        model = self.model(resource)
        if isinstance(model, (acl_mixin.AccessControlMixin,
                              AccessControlledModel)):
            obj = model.load(id, level=AccessType.READ, user=user)
        else:
            obj = model.load(id)
        version = -1
        if 'version' in params:
            if params['version'] == 'all':
                version = None
            else:
                try:
                    version = int(params['version'])
                except ValueError:
                    raise RestException('Invalid version.')
        provenance = obj.get('provenance', [])
        result = None
        if version is None or version == 0:
            result = provenance
        elif version < 0:
            if len(provenance) >= -version:
                result = provenance[version]
        else:
            for prov in provenance:
                if prov.get('version', None) == version:
                    result = prov
                    break
        return {
            'resourceId': id,
            'provenance': result
        }

    # These methods maintain the provenance

    def resourceSaveHandler(self, event):
        # get the resource name from the event
        resource = event.name.split('.')[1]
        obj = event.info
        if ('_id' not in obj or ('provenance' not in obj and
                                 obj.get('updated', None) ==
                                 obj.get('created', 'unknown'))):
            self.createNewProvenance(obj, resource)
        else:
            if 'provenance' not in obj:
                self.createExistingProvenance(obj, resource)
            elif (obj.get('updated', None) !=
                    obj['provenance'][-1].get('eventTime', False)):
                self.updateProvenance(obj, resource)

    def createNewProvenance(self, obj, resource):
        provenance = []
        created = obj.get('created', datetime.datetime.utcnow())
        creatorId = obj.get('creatorId', None)
        if creatorId is None:
            user = self.getProvenanceUser(obj)
            if user is not None:
                creatorId = user['_id']
        creationEvent = {
            'eventType': 'creation',
            'eventUser': creatorId,
            'eventTime': obj.get('updated', created),
            'created': created
        }
        obj['provenance'] = provenance
        self.addProvenanceEvent(obj, creationEvent, resource)

    def getProvenanceUser(self, obj):
        """
        Get the user that is associated with the current provenance change.
        This is the current session user, if there is one.  If not, it is the
        object's user or creator.
        :param obj: a model object.
        :returns: user for the object or None.
        """
        user = self.getCurrentUser()
        if obj and not user:
            user = obj.get('userId', None)
            if not user:
                user = obj.get('creatorId', None)
        if isinstance(user, tuple([ObjectId] + list(six.string_types))):
            user = self.model('user').load(user, force=True)
        return user

    def createExistingProvenance(self, obj, resource):
        self.createNewProvenance(obj, resource)
        # we don't know what happened between creation and now
        provenance = obj['provenance']
        provenance[0]['eventType'] = 'unknownHistory'
        # but we can track starting now
        self.updateProvenance(obj, resource)

    def addProvenanceEvent(self, obj, provenanceEvent, resource):
        if 'provenance' not in obj:
            self.createExistingProvenance(obj, resource)
        provenance = obj['provenance']
        self.incrementVersion(provenance, provenanceEvent)
        provenance.append(provenanceEvent)

    def incrementVersion(self, provenance, provenanceEvent):
        if len(provenance) == 0:
            # counting from 1, since people do that
            provenanceEvent['version'] = 1
        else:
            provenanceEvent['version'] = int(provenance[-1]['version']) + 1

    def updateProvenance(self, curObj, resource):
        """
        Update the provenance record of an object.
        :param curObj: the object to potentially update.
        :param resource: the type of resource (model name).
        :returns: True if the provenance was updated, False if it stayed the
                  same.
        """
        user = self.getProvenanceUser(curObj)
        model = self.model(resource)
        if isinstance(model, (acl_mixin.AccessControlMixin,
                              AccessControlledModel)):
            prevObj = model.load(curObj['_id'], force=True)
        else:
            prevObj = model.load(curObj['_id'])
        if prevObj is None:
            return False
        oldData, newData = self.resourceDifference(prevObj, curObj)
        if not len(newData) and not len(oldData):
            return False
        updateEvent = {
            'eventType': 'update',
            'eventTime': curObj.get('updated', datetime.datetime.utcnow()),
            'new': newData,
            'old': oldData
        }
        if user is not None:
            updateEvent['eventUser'] = user['_id']
        self.addProvenanceEvent(curObj, updateEvent, resource)
        return True

    def resourceDifference(self, prevObj, curObj):
        """
        Generate dictionaries with values that have changed between two
        objects.
        :param prevObj: the initial state of the object.
        :param curObj: the current state of the object.
        :returns: oldData: a dictionary of values that are no longer the same
                           or present in the object.
        :returns: newData: a dictionary of values that are different or new in
                           the object.
        """
        curSnapshot = self.snapshotResource(curObj)
        prevSnapshot = self.snapshotResource(prevObj)
        oldData = {}
        newData = {}
        for key in curSnapshot:
            if key in prevSnapshot:
                try:
                    if curSnapshot[key] != prevSnapshot[key]:
                        newData[key] = curSnapshot[key]
                        oldData[key] = prevSnapshot[key]
                except TypeError:
                    # If the data types of the old and new keys are not
                    # comparable, an error is thrown.  In this case, always
                    # treat them as different.
                    newData[key] = curSnapshot[key]
                    oldData[key] = prevSnapshot[key]
            else:
                newData[key] = curSnapshot[key]
        for key in prevSnapshot:
            if key not in curSnapshot:
                oldData[key] = prevSnapshot[key]
        return oldData, newData

    def snapshotResource(self, obj):
        """
        Generate a dictionary that represents an arbitrary resource.  All
        fields are included except provenance and values starting with _.
        :param obj: the object for which to generate a snapshop dictionary.
        :param includeItemFiles: if True and this is an item, include files.
        :returns: a snapshot dictionary.
        """
        ignoredKeys = ('provenance', 'updated')
        snap = {key: obj[key] for key in obj
                if not key.startswith('_') and key not in ignoredKeys}
        return snap

    def fileSaveHandler(self, event):
        """
        When a file is saved, update the provenance of the parent item.
        :param event: the event with the file information.
        """
        curFile = event.info
        if not curFile.get('itemId') or '_id' not in curFile:
            return
        user = self.getProvenanceUser(curFile)
        item = self.model('item').load(id=curFile['itemId'], force=True)
        if not item:
            return
        prevFile = self.model('file').load(curFile['_id'], force=True)
        if prevFile is None:
            oldData = None
            newData = self.snapshotResource(curFile)
        else:
            oldData, newData = self.resourceDifference(prevFile, curFile)
        if not len(newData) and not len(oldData):
            return
        updateEvent = {
            'eventType': 'fileUpdate',
            'eventTime': curFile.get('updated', datetime.datetime.utcnow()),
            'file': [{
                'fileId': curFile['_id'],
                'new': newData
            }]
        }
        if oldData is not None:
            updateEvent['file'][0]['old'] = oldData
        if user is not None:
            updateEvent['eventUser'] = user['_id']
        self.addProvenanceEvent(item, updateEvent, 'item')
        self.model('item').save(item, triggerEvents=False)

    def fileSaveCreatedHandler(self, event):
        """
        When a file is created, we don't record it in the save handler
        because we want to know its id.  We record it here, instead.
        :param event: the event with the file information.
        """
        file = event.info
        if not file.get('itemId') or '_id' not in file:
            return
        user = self.getProvenanceUser(file)
        item = self.model('item').load(id=file['itemId'], force=True)
        if not item:
            return
        updateEvent = {
            'eventType': 'fileAdded',
            'eventTime': file.get('created', datetime.datetime.utcnow()),
            'file': [{
                'fileId': file['_id'],
                'new': self.snapshotResource(file)
            }]
        }
        if user is not None:
            updateEvent['eventUser'] = user['_id']
        self.addProvenanceEvent(item, updateEvent, 'item')
        self.model('item').save(item, triggerEvents=False)

    def fileRemoveHandler(self, event):
        """
        When a file is removed, update the provenance of the parent item.
        :param event: the event with the file information.
        """
        file = event.info
        itemId = file.get('itemId')
        # Don't attach provenance to an item based on files that are not
        # directly associated (we may want to revisit this and, when files are
        # attachedToType, add provenance to the appropriate type and ID).
        if not itemId:
            return
        user = self.getProvenanceUser(file)
        item = self.model('item').load(id=itemId, force=True)
        if not item:
            return
        updateEvent = {
            'eventType': 'fileRemoved',
            'eventTime': datetime.datetime.utcnow(),
            'file': [{
                'fileId': file['_id'],
                'old': self.snapshotResource(file)
            }]
        }
        if user is not None:
            updateEvent['eventUser'] = user['_id']
        self.addProvenanceEvent(item, updateEvent, 'item')
        self.model('item').save(item, triggerEvents=False)

    def resourceCopyHandler(self, event):
        # Use the old item's provenance, but add a copy record.
        resource = event.name.split('.')[1]
        srcObj, newObj = event.info
        # We should have marked the new object already when it was first
        # created.  If not, exit
        if 'provenance' not in newObj:
            pass  # pragma: no cover
        if 'provenance' in srcObj:
            newProv = newObj['provenance'][-1]
            newObj['provenance'] = copy.deepcopy(srcObj['provenance'])
            newProv['version'] = newObj['provenance'][-1]['version'] + 1
            newObj['provenance'].append(newProv)
        # Convert the creation record to a copied record
        newObj['provenance'][-1]['eventType'] = 'copy'
        if '_id' in srcObj:
            newObj['provenance'][-1]['originalId'] = srcObj['_id']
        self.model(resource).save(newObj, triggerEvents=False)
