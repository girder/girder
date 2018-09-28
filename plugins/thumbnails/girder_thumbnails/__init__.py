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

import json
from girder import events
from girder.constants import AccessType
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.user import User
from girder.plugin import getPlugin, GirderPlugin
from girder.utility.model_importer import ModelImporter
from . import rest, utils


def removeThumbnails(event):
    """
    When a resource containing thumbnails is about to be deleted, we delete
    all of the thumbnails that are attached to it.
    """
    thumbs = event.info.get('_thumbnails', ())
    fileModel = File()

    for fileId in thumbs:
        file = fileModel.load(fileId, force=True)
        if file:
            fileModel.remove(file)


def removeThumbnailLink(event):
    """
    When a thumbnail file is deleted, we remove the reference to it from the
    resource to which it is attached.
    """
    doc = event.info

    if doc.get('isThumbnail'):
        model = ModelImporter.model(doc['attachedToType'])
        resource = model.load(doc['attachedToId'], force=True)

        if doc['_id'] in resource.get('_thumbnails', ()):
            resource['_thumbnails'].remove(doc['_id'])
            model.save(resource, validate=False)


def _onUpload(event):
    """
    Thumbnail creation can be requested on file upload by passing a reference field
    that is a JSON object of the following form:

        {
          "thumbnail": {
            "width": 123,
            "height": 123,
            "crop": True
          }
        }

    At least one of ``width`` or ``height`` must be passed. The ``crop`` parameter is optional.
    """
    file = event.info['file']
    if 'itemId' not in file:
        return

    try:
        ref = json.loads(event.info.get('reference', ''))
    except ValueError:
        return

    if not isinstance(ref, dict) or not isinstance(ref.get('thumbnail'), dict):
        return

    width = max(0, ref['thumbnail'].get('width', 0))
    height = max(0, ref['thumbnail'].get('height', 0))

    if not width and not height:
        return
    if not isinstance(width, int) or not isinstance(height, int):
        return

    item = Item().load(file['itemId'], force=True)
    crop = bool(ref['thumbnail'].get('crop', True))
    utils.scheduleThumbnailJob(
        file=file, attachToType='item', attachToId=item['_id'], user=event.info['currentUser'],
        width=width, height=height, crop=crop)


class ThumbnailsPlugin(GirderPlugin):
    DISPLAY_NAME = 'Thumbnails'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        getPlugin('jobs').load(info)

        name = 'thumbnails'
        info['apiRoot'].thumbnail = rest.Thumbnail()

        for model in (Item(), Collection(), Folder(), User()):
            model.exposeFields(level=AccessType.READ, fields='_thumbnails')
            events.bind('model.%s.remove' % model.name, name, removeThumbnails)

        events.bind('model.file.remove', name, removeThumbnailLink)
        events.bind('data.process', name, _onUpload)
