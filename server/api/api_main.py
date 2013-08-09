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

from v1 import user as user1,\
               folder as folder1,\
               api_docs as api_docs1

class ApiDocs():
    exposed = True

    def GET(self):
        # TODO
        return "should display links to available api versions"

def addApiToNode(node):
    node.api = ApiDocs()
    node.api = _addV1ToNode(node.api)

    return node

def _addV1ToNode(node):
    node.v1 = api_docs1.ApiDocs()
    node.v1.user = user1.User()
    node.v1.folder = folder1.Folder()

    return node
