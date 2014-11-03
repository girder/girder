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

from . import constants
from girder import events
from girder.api.describe import Description
from girder.api.rest import Resource
from girder.api import access
from girder.constants import AccessType
from girder.models.model_base import ValidationException


def validateSettings(event):
    key, val = event.info['key'], event.info['value']

    if key == constants.PluginSettings.PROVENANCE_RESOURCES:
        if val:
            if not isinstance(val, basestring):
                raise ValidationException(
                    'Provenance Resources list must be empty or a valid JSON '
                    'list of strings.', 'value')
            # accept comma or space separated lists
            resources = val.replace(",", " ").strip().split()
            # reformat to a comma-separated list
            event.info["value"] = ",".join(resources)
        event.preventDefault().stopPropagation()


class ResourceExt(Resource):
    def __init__(self, info):
        """
        Initialize the resource.  This saves the info path so that we can
        dynamically change the routes when the setting listing the resources we
        use changes.
        :param info: the info class passed to the load function.
        """
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
        for disallowedResource in ('model_base', ):
            if disallowedResource in resources:
                del resources[disallowedResource]
        # iterate on keys() so that we can change the dictionary as we use it
        for oldresource in self.boundResources.keys():
            if oldresource not in resources:
                # Unbind this and remove it from the api
                events.unbind('model.{}.save'.format(oldresource), 'provenance')
                getattr(self.loadInfo['apiRoot'], oldresource).removeRoute(
                    'GET', (':id', 'provenance'),
                    self.getGetHandler(oldresource))
                del self.boundResources[oldresource]
        for resource in resources:
            if (resource not in self.boundResources and
                    hasattr(self.loadInfo['apiRoot'], resource)):
                events.bind('model.{}.save'.format(resource), 'provenance',
                            self.resourceSaveHandler)
                getattr(self.loadInfo['apiRoot'], resource).route(
                    'GET', (':id', 'provenance'), self.getGetHandler(resource))
                self.boundResources[resource] = True
        # ##DWM:: We may want to always add a resource route

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
    def provenanceGetHandler(self, id, params, resource=None):
        user = self.getCurrentUser()
        obj = self.model(resource).load(id, level=AccessType.READ, user=user)
        # Handle provenance level ##DWM::
        return {
            'resourceId': id,
            'provenance': obj.get('provenance', [])[-1:]
        }
    provenanceGetHandler.description = (
        Description('Get the provenance for a given resource.')
        .param('id', 'The resource ID', paramType='path')
        .param('provenance', 'The provenance version for the resource.  If '
               'not specified, the latest provenance data is returned.  If '
               '"all" is specified, a list of all provenance data is '
               'returned.', required=False)
        .errorResponse())

    # These methods maintain the provenance

    def resourceSaveHandler(self, event):
        resource = event.name.split('.')[1]
        # event has our model in it
        obj = event.info
        if ('_id' not in obj or ('provenance' not in obj and
                                 obj['updated'] == obj['created'])):
            self.createNewProvenance(obj, resource)
        else:
            if 'provenance' not in obj:
                self.createExistingProvenance(obj, resource)
            elif obj['updated'] != obj['provenance'][-1]['updated']:
                self.updateProvenance(obj, resource)

    def createNewProvenance(self, obj, resource):
        provenance = []
        creationEvent = {
            'eventType': 'creation',
            'createdBy': obj['creatorId'],
            'created': obj['created'],
            'updated': obj['updated'],
        }
        obj['provenance'] = provenance
        self.addProvenanceEvent(obj, creationEvent)

    def createExistingProvenance(self, obj, resource):
        self.createNewProvenance(obj, resource)
        # we don't know what happenened between creation and now
        provenance = obj['provenance']
        provenance[0]['eventType'] = 'unknownHistory'
        # but we can track starting now
        self.updateProvenance(obj, resource)

    def addProvenanceEvent(self, obj, provenanceEvent):
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
        user = self.getCurrentUser()
        prevObj = self.model(resource).load(curObj['_id'],
                                            level=AccessType.READ, user=user)
        if prevObj is None:
            return
        curSnapshot = self.snapshotResource(curObj, resource)
        prevSnapshot = self.snapshotResource(prevObj, resource)
        oldData = {}
        newData = {}
        for key in curSnapshot:
            if key not in prevSnapshot:
                newData[key] = curSnapshot[key]
            elif curSnapshot[key] != prevSnapshot[key]:
                newData[key] = curSnapshot[key]
                oldData[key] = prevSnapshot[key]
        for key in prevSnapshot:
            if key not in curSnapshot:
                oldData[key] = prevSnapshot[key]
        if not len(newData) and not len(oldData):
            return
        updateEvent = {
            'eventType': 'update',
            'updated': curObj['updated'],
            'new': newData,
            'old': oldData
        }
        if user is not None:
            updateEvent['updatedBy'] = user['_id']
        self.addProvenanceEvent(curObj, updateEvent)

    def snapshotResource(self, obj, resource):
        """
        Generate a dictionary that represents an arbitrary resource.  All
        fields are included except provenance and values starting with _.
        :param obj: the object for which to generate a snapshop dictionary.
        :param resource: the resource (model) type.  'item' objects are
                         treated specially to include file information.
        :returns: a snapshot dictionary.
        """
        ignoredKeys = ('provenance', 'updated')
        snap = {key: obj[key] for key in obj
                if not key.startswith('_') and key not in ignoredKeys}
        if resource == 'item':
            pass
            # ##DWM:: get file info
        return snap


def load(info):
    events.bind('model.setting.validate', 'provenance', validateSettings)
    ext = ResourceExt(info)
    events.bind('model.setting.save.after', 'provenance', ext.bindModels)
    events.bind('provenance.initialize', 'provenance', ext.bindModels)
    events.trigger('provenance.initialize', info={})
