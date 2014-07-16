#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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

from girder.constants import AccessType
from girder.utility.model_importer import ModelImporter
from girder import events
from girder.api.describe import Description
from girder.api.rest import Resource, RestException

class ResourceExt(Resource):

    def __init__(self):
        self.itemModel = ModelImporter().model('item')

    def incrementVersion(self, provenance, provenanceEvent):
        if len(provenance) == 0:
            # counting from 1, since people do that
            provenanceEvent['version'] = '1'
        else:
            prevVersion = provenance[-1]['version']
            currVersion = int(prevVersion) + 1
            provenanceEvent['version'] = currVersion

    def snapshotItemMeta(self, item, provenanceEvent):
        provenanceEvent['meta'] = item['meta']

    def snapshotItem(self, item, provenanceEvent):
        # TODO: keep in sync with versioningChangesExist
        if 'meta' in item:
            self.snapshotItemMeta(item, provenanceEvent)

    def metadataDiffsExist(self, prevItem, currItem):
        prevMetaEmpty = 'meta' not in prevItem or len(prevItem['meta']) == 0
        currMetaEmpty = 'meta' not in currItem or len(currItem['meta']) == 0
        if prevMetaEmpty and currMetaEmpty:
            return False
        if prevMetaEmpty != currMetaEmpty:
            return True
        prevMeta = prevItem['meta']
        currMeta = currItem['meta']
        prevMetaSet = set(prevMeta)
        currMetaSet = set(currMeta)
        if len(prevMetaSet.intersection(currMetaSet)) != len(prevMetaSet):
            return True
        return any([True for key in prevMeta.keys() if prevMeta[key] != currMeta[key]])

    def versioningChangesExist(self, prevItem, currItem):
        # TODO: keep in sync with snapshotItem
        #
        # if any changes in the following exist, create a new version
        #
        # metadata
        # TODO: file itself
        #
        if self.metadataDiffsExist(prevItem, currItem):
            return True
        return False

    def addProvenanceEvent(self, item, provenanceEvent):
        provenance = item['provenance']
        self.snapshotItem(item, provenanceEvent)
        self.incrementVersion(provenance, provenanceEvent)
        provenance.append(provenanceEvent)

    def createNewItemProvenance(self, item):
        provenance = []
        creationEvent = {
          'eventType': 'creation',
          'createdBy': item['creatorId'],
          'created': item['created'],
          'createdIn': item['folderId'],
          'updated': item['updated'],
        }
        item['provenance'] = provenance
        self.addProvenanceEvent(item, creationEvent)

    def createExistingItemProvenance(self, item):
        self.createNewItemProvenance(item)
        # we don't know what happenened between creation and now
        provenance = item['provenance']
        provenance[0]['eventType'] = 'unknownHistory'
        # but we can track starting now
        self.updateItemProvenance(item)

    def updateItemProvenance(self, currItem):
        user = self.getCurrentUser()
        prevItem = self.itemModel.load(currItem['_id'], level=AccessType.READ, user=user)
        if self.versioningChangesExist(prevItem, currItem):
            provenance = currItem['provenance']
            provUpdateEvent = {
                'eventType': 'update',
                'updatedBy': user['_id'],
                'updated': currItem['updated']
            }
            self.addProvenanceEvent(currItem, provUpdateEvent)

    def itemSaveHandler(self, event):
        item = event.info    
        if '_id' not in item or ('provenance' not in item and item['updated'] == item['created']):
            self.createNewItemProvenance(item)
        else:
            if 'provenance' not in item:
                self.createExistingItemProvenance(item)
            elif item['updated'] != item['provenance'][-1]['updated']:
                self.updateItemProvenance(item)

    def provenanceGetHandler(self, id, params):
        user = self.getCurrentUser()
        item = self.itemModel.load(id, level=AccessType.READ, user=user)
        return {
            'itemId': id,
            'provenance': item['provenance']
        }

    provenanceGetHandler.description = (
        Description('Get the provenance for a given item.')
        .param('id', 'The item ID', paramType='path')
        .param('provenance', 'The provenance for the item with passed in ID', required=False)
        .errorResponse())

def load(info):
    ext = ResourceExt()
    events.bind('model.item.save', 'provenance', ext.itemSaveHandler)
    info['apiRoot'].item.route('GET', (':id', 'provenance'), ext.provenanceGetHandler)