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

from .model_base import AccessControlledModel, ValidationException

class Folder(AccessControlledModel):

    def initialize(self):
        self.name = 'folder'
        self.setIndexedFields(['parentId'])

    def validate(self, doc):
        doc['name'] = doc['name'].strip()
        doc['description'] = doc['description'].strip()

        if not doc['name']:
            raise ValidationException('Folder name must not be empty.', 'name')

        if not doc['parentCollection'] in ('folder', 'user', 'community'):
            # Internal error; this shouldn't happen
            raise Exception('Invalid folder parent type: %s.' % doc['parentCollection'])

        q = {
            'parentId' : doc['parentId'],
            'name' : doc['name'],
            'parentCollection' : doc['parentCollection']
            }
        if doc.has_key('_id'):
            q['_id'] = {'$ne' : doc['parentId']}
        duplicates = self.find(q, limit=1, fields=['_id'])
        if duplicates.count() != 0:
            raise ValidationException('A folder with that name already exists here.')

        # TODO validate that no sibling ITEM has the requested name either

        return doc

    def createFolder(self, parent, name, description='', parentType='folder', public=None,
                     creator=None):
        """
        Create a new folder under the given parent.
        :param parent: The parent document. Should be a folder, user, or community.
        :type parent: dict
        :param name: The name of the folder.
        :type name: str
        :param description: Description for the folder.
        :type description: str
        :param parentType: What type the parent is: ('folder' | 'user' | 'community')
        :type parentType: str
        :param public: Public read access flag.
        :type public: bool or None to inherit from parent
        :param creator: User document representing the creator of this folder.
        :type creator: dict
        :returns: The folder document that was created.
        """
        assert parent.has_key('_id')
        assert public is None or type(public) is bool

        now = datetime.datetime.now()

        if creator is None:
            creatorId = None
        else:
            creatorId = creator.get('_id', None)

        folder = {
            'name' : name,
            'description' : description,
            'parentCollection' : parentType,
            'parentId' : parent['_id'],
            'creatorId' : creatorId,
            'created' : now,
            'updated' : now,
            'size' : 0
            }

        # If this is a subfolder, default permissions are inherited from the parent folder
        if parentType == 'folder':
            folder = self.copyAccessPolicies(src=parent, dest=folder, save=False)

        # Allow explicit public flag override if it's set.
        if public is not None and type(public) is bool:
            folder['public'] = public

        # Now validate and save the folder.
        folder = self.save(folder)

        return folder
