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

import cherrypy

from . import describe
from .v1 import api_key, assetstore, file, collection, folder, group, item,\
    resource, system, token, user, notification


class ApiDocs(object):
    exposed = True

    def GET(self):
        # Since we only have v1 right now, just redirect to the v1 page.
        # If we get more versions, this should show an index of them.
        raise cherrypy.HTTPRedirect(cherrypy.url() + '/v1')


def addApiToNode(node):
    node.api = ApiDocs()
    _addV1ToNode(node.api)

    return node


def _addV1ToNode(node):
    node.v1 = describe.ApiDocs()
    node.v1.describe = describe.Describe()

    node.v1.api_key = api_key.ApiKey()
    node.v1.assetstore = assetstore.Assetstore()
    node.v1.collection = collection.Collection()
    node.v1.file = file.File()
    node.v1.folder = folder.Folder()
    node.v1.group = group.Group()
    node.v1.item = item.Item()
    node.v1.notification = notification.Notification()
    node.v1.resource = resource.Resource()
    node.v1.system = system.System()
    node.v1.token = token.Token()
    node.v1.user = user.User()

    return node
